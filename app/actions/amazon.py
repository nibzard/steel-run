"""Amazon automation actions using Steel and Claude Computer Use."""

import json
import time
from typing import Any
from urllib.parse import urlparse

import structlog

from ..agent.executor import BrowserSession, ClaudeAgent
from .base import ActionExecutionError, ActionValidationError, BaseAction

logger = structlog.get_logger(__name__)


class AmazonPriceCheckAction(BaseAction):
    """Check product price on Amazon using browser automation."""

    # Action metadata
    name = "Amazon Price Check"
    description = "Check the current price and availability of a product on Amazon"
    category = "e_commerce"
    tags = ["amazon", "price", "product", "shopping", "monitoring"]

    # Performance settings
    timeout_seconds = 90  # Amazon can be slow with anti-bot measures
    estimated_duration_seconds = 45
    success_rate_threshold = 0.75  # Lower due to Amazon's anti-bot measures

    # Parameter schema
    parameters = {
        "product_search": {
            "type": "string",
            "required": False,
            "min_length": 3,
            "max_length": 200,
            "description": "Product name or search query to find on Amazon"
        },
        "product_url": {
            "type": "string",
            "required": False,
            "description": "Direct Amazon product URL (alternative to search)"
        },
        "region": {
            "type": "string",
            "required": False,
            "description": "Amazon region (com, co.uk, de, etc.)"
        },
        "include_reviews": {
            "type": "boolean",
            "required": False,
            "description": "Include review count and rating in results"
        },
        "include_variants": {
            "type": "boolean",
            "required": False,
            "description": "Include price information for product variants"
        }
    }

    async def execute(self, product_search: str | None = None,
                     product_url: str | None = None,
                     region: str = "com",
                     include_reviews: bool = True,
                     include_variants: bool = False) -> dict[str, Any]:
        """
        Execute the Amazon price check action.

        Args:
            product_search: Product search query
            product_url: Direct product URL
            region: Amazon region
            include_reviews: Include review data
            include_variants: Include variant pricing

        Returns:
            Dict containing price information and screenshots
        """
        if not product_search and not product_url:
            raise ActionValidationError(
                "Either 'product_search' or 'product_url' must be provided",
                parameter="product_search"
            )

        if product_url and not self._is_valid_amazon_url(product_url, region):
            raise ActionValidationError(
                "Invalid Amazon URL provided",
                parameter="product_url"
            )

        logger.info("Starting Amazon price check action",
                   search=product_search,
                   url=product_url,
                   region=region,
                   session_id=self.session_id)

        # Create Steel browser session optimized for Amazon
        session_id = await self.create_session(
            use_proxy=True,
            solve_captcha=True,
            stealth_config={
                "humanize_interactions": True,
                "skip_fingerprint_injection": False,
                "random_user_agent": True
            },
            dimensions={"width": 1920, "height": 1080},
            api_timeout=90000,  # 90 second timeout
            region=region  # Use appropriate region for Amazon
        )

        try:
            # Initialize browser session and Claude agent
            browser_session = BrowserSession(self.steel, session_id)
            agent = ClaudeAgent(browser_session)

            # Execute the price check task
            task_description = self._build_price_check_task_description(
                product_search, product_url, region, include_reviews, include_variants
            )
            context = {
                "action": "amazon_price_check",
                "product_search": product_search,
                "product_url": product_url,
                "region": region,
                "include_reviews": include_reviews,
                "include_variants": include_variants,
                "platform": f"amazon.{region}"
            }

            result = await agent.execute_task(task_description, context)

            # Process and format the result
            return await self._process_price_result(result, product_search or product_url)

        except Exception as e:
            logger.error("Amazon price check action failed", error=str(e), session_id=session_id)

            # Capture error screenshot
            error_screenshot = await self.capture_screenshot()

            raise ActionExecutionError(
                f"Failed to check Amazon price: {str(e)}",
                error_code="AMAZON_PRICE_ERROR",
                details={
                    "product_search": product_search,
                    "product_url": product_url,
                    "region": region,
                    "error_screenshot": error_screenshot,
                    "session_id": session_id
                }
            )

    def _is_valid_amazon_url(self, url: str, region: str = "com") -> bool:
        """Validate that URL is a valid Amazon product URL."""
        try:
            parsed = urlparse(url.lower())
            valid_domains = [f"amazon.{region}", f"www.amazon.{region}"]

            if parsed.netloc not in valid_domains:
                return False

            # Check for product URL patterns
            product_patterns = ["/dp/", "/gp/product/", "/product/"]
            return any(pattern in parsed.path for pattern in product_patterns)

        except Exception:
            return False

    def _build_price_check_task_description(self, product_search: str | None,
                                          product_url: str | None,
                                          region: str,
                                          include_reviews: bool,
                                          include_variants: bool) -> str:
        """Build detailed task description for Claude price checking."""

        base_url = f"https://amazon.{region}"

        if product_url:
            task = f"""
Complete an Amazon price check task for a specific product:

1. NAVIGATE to the product URL: {product_url}
2. WAIT for the page to fully load and handle any captchas/verification
3. EXTRACT the following product information:
   - Product title and brand
   - Current price (handle various price formats)
   - Availability status (in stock, out of stock, limited)
   - Prime shipping availability
   - Seller information (Amazon, third-party, etc.)
   {"- Review rating and review count" if include_reviews else ""}
   {"- Variant prices and options (size, color, etc.)" if include_variants else ""}
4. TAKE screenshots showing the product details and pricing
5. VERIFY all extracted information is accurate

IMPORTANT REQUIREMENTS:
- Handle Amazon's anti-bot measures gracefully
- Extract exact pricing information (watch for sales, discounts)
- Note if the product has multiple sellers with different prices
- Handle regional pricing and currency correctly
- Take clear screenshots of the product page
- If blocked by Amazon, try refreshing or waiting briefly
"""
        else:
            task = f"""
Complete an Amazon price check task by searching for a product:

1. NAVIGATE to Amazon.{region} ({base_url})
2. SEARCH for the product: "{product_search}"
3. SELECT the most relevant product from search results
4. EXTRACT the following product information:
   - Product title and brand
   - Current price (handle various price formats)
   - Availability status (in stock, out of stock, limited)
   - Prime shipping availability
   - Seller information (Amazon, third-party, etc.)
   {"- Review rating and review count" if include_reviews else ""}
   {"- Variant prices and options (size, color, etc.)" if include_variants else ""}
5. TAKE screenshots showing search results and selected product
6. VERIFY all extracted information is accurate

SEARCH QUERY: "{product_search}"

IMPORTANT REQUIREMENTS:
- Use exact search term: "{product_search}"
- Select the most relevant/popular product result
- Handle Amazon's anti-bot measures gracefully
- Extract exact pricing information (watch for sales, discounts)
- Note if the product has multiple sellers with different prices
- Handle regional pricing and currency correctly
- Take clear screenshots of search and product pages
"""

        task += f"""

REGIONAL SETTINGS:
- Target Amazon region: amazon.{region}
- Handle regional currency and shipping information
- Respect local Amazon layout variations

SUCCESS CRITERIA:
- Successfully accessed Amazon without being blocked
- Found and accessed the correct product
- Extracted accurate pricing and availability data
- {"Collected review information" if include_reviews else ""}
- {"Analyzed variant pricing" if include_variants else ""}
- Clear screenshots documenting the process

ERROR HANDLING:
- If encountering captchas, solve them or report the need for manual intervention
- If products are out of stock, still collect available information
- If pricing is unavailable, note the reason (region restrictions, etc.)
- Handle Amazon's various page layouts and A/B tests

ANTI-DETECTION:
- Use human-like interaction patterns
- Add realistic delays between actions
- Handle any Amazon security challenges appropriately
"""

        return task.strip()

    async def _process_price_result(self, agent_result: dict[str, Any],
                                   search_term: str) -> dict[str, Any]:
        """Process Claude agent result for Amazon price checking."""

        status = agent_result.get("status", "failed")
        claude_message = agent_result.get("message", "No message provided")
        screenshots = agent_result.get("screenshots", [])
        evidence = agent_result.get("evidence", {})

        # Extract product information from Claude's response
        # In a real implementation, this would parse structured data
        # from Claude's analysis of the Amazon page

        result_data = {
            "search_term": search_term,
            "amazon_url": agent_result.get("final_url"),
            "product_title": evidence.get("product_title", "Unknown"),
            "current_price": evidence.get("current_price"),
            "currency": evidence.get("currency", "USD"),
            "availability": evidence.get("availability", "Unknown"),
            "prime_shipping": evidence.get("prime_shipping", False),
            "seller": evidence.get("seller", "Unknown"),
            "review_rating": evidence.get("review_rating") if evidence.get("include_reviews") else None,
            "review_count": evidence.get("review_count") if evidence.get("include_reviews") else None,
            "variants": evidence.get("variants", []) if evidence.get("include_variants") else [],
            "extracted_at": time.time(),
            "iterations": agent_result.get("iterations", 0)
        }

        # Determine success message
        if status == "success":
            if result_data["current_price"]:
                success_message = f"Found {result_data['product_title']} for {result_data['currency']} {result_data['current_price']}"
            else:
                success_message = f"Found product information for {search_term}"
        else:
            success_message = f"Failed to check Amazon price: {claude_message}"

        # Get final screenshot
        final_screenshot = None
        if screenshots:
            final_screenshot = screenshots[-1].get("image_b64") if screenshots[-1] else None

        if not final_screenshot:
            final_screenshot = await self.capture_screenshot()

        return {
            "status": status,
            "message": success_message,
            "data": result_data,
            "screenshot": final_screenshot,
            "timestamp": time.time(),
            "execution_details": {
                "screenshots_captured": len(screenshots),
                "claude_response": claude_message,
                "session_id": self.session_id
            }
        }


class AmazonProductDetailsAction(BaseAction):
    """Extract detailed product information from Amazon including reviews and specifications."""

    # Action metadata
    name = "Amazon Product Details"
    description = "Extract comprehensive product details, reviews, and specifications from Amazon"
    category = "e_commerce"
    tags = ["amazon", "product", "details", "reviews", "specifications"]

    # Performance settings
    timeout_seconds = 120  # Longer timeout for detailed extraction
    estimated_duration_seconds = 60
    success_rate_threshold = 0.70

    # Parameter schema
    parameters = {
        "product_url": {
            "type": "string",
            "required": True,
            "description": "Amazon product URL to analyze"
        },
        "include_reviews": {
            "type": "boolean",
            "required": False,
            "description": "Extract customer review summaries"
        },
        "include_qa": {
            "type": "boolean",
            "required": False,
            "description": "Include customer questions and answers"
        },
        "include_specs": {
            "type": "boolean",
            "required": False,
            "description": "Extract technical specifications"
        },
        "max_reviews": {
            "type": "integer",
            "required": False,
            "min_value": 1,
            "max_value": 50,
            "description": "Maximum number of reviews to extract"
        }
    }

    async def execute(self, product_url: str, include_reviews: bool = True,
                     include_qa: bool = False, include_specs: bool = True,
                     max_reviews: int = 10) -> dict[str, Any]:
        """
        Execute the Amazon product details extraction.

        Args:
            product_url: Amazon product URL
            include_reviews: Extract review information
            include_qa: Include Q&A section
            include_specs: Include specifications
            max_reviews: Maximum reviews to extract

        Returns:
            Dict containing detailed product information
        """
        if not self._is_valid_amazon_url(product_url):
            raise ActionValidationError(
                "Invalid Amazon product URL provided",
                parameter="product_url"
            )

        logger.info("Starting Amazon product details extraction",
                   url=product_url,
                   include_reviews=include_reviews,
                   session_id=self.session_id)

        # Create Steel browser session
        session_id = await self.create_session(
            use_proxy=True,
            solve_captcha=True,
            stealth_config={
                "humanize_interactions": True,
                "skip_fingerprint_injection": False,
                "random_user_agent": True
            },
            dimensions={"width": 1920, "height": 1080},
            api_timeout=120000
        )

        try:
            browser_session = BrowserSession(self.steel, session_id)
            agent = ClaudeAgent(browser_session)

            task_description = self._build_details_task_description(
                product_url, include_reviews, include_qa, include_specs, max_reviews
            )
            context = {
                "action": "amazon_product_details",
                "product_url": product_url,
                "include_reviews": include_reviews,
                "include_qa": include_qa,
                "include_specs": include_specs,
                "max_reviews": max_reviews
            }

            result = await agent.execute_task(task_description, context)

            return await self._process_details_result(result, product_url)

        except Exception as e:
            logger.error("Amazon product details action failed", error=str(e), session_id=session_id)

            error_screenshot = await self.capture_screenshot()

            raise ActionExecutionError(
                f"Failed to extract Amazon product details: {str(e)}",
                error_code="AMAZON_DETAILS_ERROR",
                details={
                    "product_url": product_url,
                    "error_screenshot": error_screenshot,
                    "session_id": session_id
                }
            )

    def _is_valid_amazon_url(self, url: str) -> bool:
        """Validate Amazon product URL."""
        try:
            parsed = urlparse(url.lower())
            amazon_domains = ["amazon.com", "www.amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr"]

            if not any(domain in parsed.netloc for domain in amazon_domains):
                return False

            product_patterns = ["/dp/", "/gp/product/", "/product/"]
            return any(pattern in parsed.path for pattern in product_patterns)

        except Exception:
            return False

    def _build_details_task_description(self, product_url: str, include_reviews: bool,
                                       include_qa: bool, include_specs: bool,
                                       max_reviews: int) -> str:
        """Build task description for detailed product extraction."""

        task = f"""
Complete a comprehensive Amazon product details extraction:

1. NAVIGATE to the product page: {product_url}
2. WAIT for complete page load and handle any Amazon security measures
3. EXTRACT comprehensive product information:

BASIC PRODUCT INFO:
- Full product title and brand
- Model/SKU number if available
- Product category and subcategory
- Current price, original price, discount percentage
- Availability and shipping information
- Prime eligibility
- Seller information and ratings

PRODUCT IMAGES:
- Main product image URL
- Count of additional product images
- Key image types (lifestyle, detail, size chart, etc.)

{"PRODUCT SPECIFICATIONS:" if include_specs else ""}
{"""- Technical specifications from product details
- Dimensions, weight, materials
- Features and key selling points
- Compatibility information
- Warranty and support details""" if include_specs else ""}

{"CUSTOMER REVIEWS (up to " + str(max_reviews) + " reviews):" if include_reviews else ""}
{"""- Overall rating and rating distribution (5-star breakdown)
- Total review count
- Recent review summaries with ratings
- Common positive and negative themes
- Verified purchase indicators""" if include_reviews else ""}

{"CUSTOMER Q&A:" if include_qa else ""}
{"""- Recent customer questions and answers
- Most helpful Q&A pairs
- Common question themes""" if include_qa else ""}

4. NAVIGATE through different sections as needed:
   - Product details/specifications tab
   {"- Customer reviews section" if include_reviews else ""}
   {"- Customer Q&A section" if include_qa else ""}

5. TAKE screenshots of each section visited

EXTRACTION REQUIREMENTS:
- Handle Amazon's dynamic content loading
- Extract exact text and numerical data
- Note any missing information sections
- Handle regional variations in layout
- Respect Amazon's rate limiting

SUCCESS CRITERIA:
- Collected comprehensive product information
- {"Extracted review data and sentiment" if include_reviews else ""}
- {"Gathered Q&A information" if include_qa else ""}
- {"Compiled technical specifications" if include_specs else ""}
- Clear screenshots documenting extraction process
- Structured data ready for processing

ERROR HANDLING:
- Handle missing sections gracefully
- Note unavailable data clearly
- Work around Amazon security measures
- Handle partial data extraction scenarios
"""

        return task.strip()

    async def _process_details_result(self, agent_result: dict[str, Any],
                                    product_url: str) -> dict[str, Any]:
        """Process Claude agent result for product details extraction."""

        status = agent_result.get("status", "failed")
        claude_message = agent_result.get("message", "No message provided")
        screenshots = agent_result.get("screenshots", [])
        evidence = agent_result.get("evidence", {})

        # Build comprehensive result data
        result_data = {
            "product_url": product_url,
            "extraction_timestamp": time.time(),

            # Basic product info
            "title": evidence.get("product_title", "Unknown"),
            "brand": evidence.get("brand"),
            "model": evidence.get("model"),
            "category": evidence.get("category"),
            "current_price": evidence.get("current_price"),
            "original_price": evidence.get("original_price"),
            "discount_percentage": evidence.get("discount_percentage"),
            "currency": evidence.get("currency", "USD"),
            "availability": evidence.get("availability"),
            "prime_eligible": evidence.get("prime_eligible", False),
            "seller_info": evidence.get("seller_info", {}),

            # Product images
            "main_image_url": evidence.get("main_image_url"),
            "image_count": evidence.get("image_count", 0),
            "image_types": evidence.get("image_types", []),

            # Specifications
            "specifications": evidence.get("specifications", {}),
            "features": evidence.get("features", []),
            "dimensions": evidence.get("dimensions", {}),
            "warranty": evidence.get("warranty"),

            # Reviews
            "review_summary": evidence.get("review_summary", {}),
            "recent_reviews": evidence.get("recent_reviews", []),
            "rating_distribution": evidence.get("rating_distribution", {}),

            # Q&A
            "qa_pairs": evidence.get("qa_pairs", []),
            "common_questions": evidence.get("common_questions", []),

            # Metadata
            "sections_extracted": evidence.get("sections_extracted", []),
            "extraction_completeness": evidence.get("completeness_score", 0),
            "iterations": agent_result.get("iterations", 0)
        }

        # Success message
        if status == "success":
            success_message = f"Successfully extracted details for {result_data['title'][:50]}..."
        else:
            success_message = f"Failed to extract product details: {claude_message}"

        # Get final screenshot
        final_screenshot = None
        if screenshots:
            final_screenshot = screenshots[-1].get("image_b64") if screenshots[-1] else None

        if not final_screenshot:
            final_screenshot = await self.capture_screenshot()

        return {
            "status": status,
            "message": success_message,
            "data": result_data,
            "screenshot": final_screenshot,
            "timestamp": time.time(),
            "execution_details": {
                "screenshots_captured": len(screenshots),
                "claude_response": claude_message,
                "session_id": self.session_id
            }
        }


class AmazonCartManagementAction(BaseAction):
    """Add products to Amazon cart and manage cart contents."""

    # Action metadata
    name = "Amazon Cart Management"
    description = "Add products to Amazon cart, view cart, and manage quantities"
    category = "e_commerce"
    tags = ["amazon", "cart", "shopping", "add", "management"]

    # Authentication required for cart operations
    requires_auth = True

    # Performance settings
    timeout_seconds = 90
    estimated_duration_seconds = 30
    success_rate_threshold = 0.70

    # Parameter schema
    parameters = {
        "action": {
            "type": "string",
            "required": True,
            "description": "Cart action: 'add_product', 'view_cart', 'update_quantity', 'remove_item'"
        },
        "product_url": {
            "type": "string",
            "required": False,
            "description": "Amazon product URL (required for add_product)"
        },
        "quantity": {
            "type": "integer",
            "required": False,
            "min_value": 1,
            "max_value": 30,
            "description": "Product quantity (for add/update operations)"
        },
        "variant_selection": {
            "type": "object",
            "required": False,
            "description": "Product variant selection (size, color, etc.)"
        },
        "credentials": {
            "type": "object",
            "required": True,
            "properties": {
                "username": {"type": "string", "required": True},
                "password": {"type": "string", "required": True}
            },
            "description": "Amazon login credentials"
        }
    }

    async def execute(self, action: str, credentials: dict[str, str],
                     product_url: str | None = None, quantity: int = 1,
                     variant_selection: dict | None = None) -> dict[str, Any]:
        """
        Execute Amazon cart management actions.

        Args:
            action: Cart action to perform
            credentials: Amazon login credentials
            product_url: Product URL (for add operations)
            quantity: Product quantity
            variant_selection: Product variant options

        Returns:
            Dict containing cart operation results
        """
        valid_actions = ["add_product", "view_cart", "update_quantity", "remove_item"]
        if action not in valid_actions:
            raise ActionValidationError(
                f"Invalid action. Must be one of: {', '.join(valid_actions)}",
                parameter="action"
            )

        if action == "add_product" and not product_url:
            raise ActionValidationError(
                "product_url is required for add_product action",
                parameter="product_url"
            )

        if product_url and not self._is_valid_amazon_url(product_url):
            raise ActionValidationError(
                "Invalid Amazon product URL provided",
                parameter="product_url"
            )

        logger.info("Starting Amazon cart management action",
                   action=action,
                   url=product_url,
                   quantity=quantity,
                   session_id=self.session_id)

        # Create Steel browser session
        session_id = await self.create_session(
            use_proxy=True,
            solve_captcha=True,
            stealth_config={
                "humanize_interactions": True,
                "skip_fingerprint_injection": False
            },
            dimensions={"width": 1920, "height": 1080},
            api_timeout=90000
        )

        try:
            browser_session = BrowserSession(self.steel, session_id)
            agent = ClaudeAgent(browser_session)

            task_description = self._build_cart_task_description(
                action, credentials, product_url, quantity, variant_selection
            )
            context = {
                "action": "amazon_cart_management",
                "cart_action": action,
                "product_url": product_url,
                "quantity": quantity,
                "variant_selection": variant_selection
            }

            result = await agent.execute_task(task_description, context)

            return await self._process_cart_result(result, action, product_url)

        except Exception as e:
            logger.error("Amazon cart management action failed", error=str(e), session_id=session_id)

            error_screenshot = await self.capture_screenshot()

            raise ActionExecutionError(
                f"Failed to manage Amazon cart: {str(e)}",
                error_code="AMAZON_CART_ERROR",
                details={
                    "action": action,
                    "product_url": product_url,
                    "error_screenshot": error_screenshot,
                    "session_id": session_id
                }
            )

    def _is_valid_amazon_url(self, url: str) -> bool:
        """Validate Amazon product URL."""
        try:
            parsed = urlparse(url.lower())
            amazon_domains = ["amazon.com", "www.amazon.com"]

            if not any(domain in parsed.netloc for domain in amazon_domains):
                return False

            product_patterns = ["/dp/", "/gp/product/", "/product/"]
            return any(pattern in parsed.path for pattern in product_patterns)

        except Exception:
            return False

    def _build_cart_task_description(self, action: str, credentials: dict[str, str],
                                   product_url: str | None, quantity: int,
                                   variant_selection: dict | None) -> str:
        """Build task description for cart management."""

        base_task = f"""
Complete Amazon cart management task - Action: {action}

1. NAVIGATE to Amazon.com
2. LOGIN with provided credentials if not already logged in
"""

        if action == "add_product":
            task = base_task + f"""
3. NAVIGATE to the product page: {product_url}
4. SELECT product variants if needed:
   {json.dumps(variant_selection, indent=2) if variant_selection else "No specific variants required"}
5. SET quantity to {quantity}
6. CLICK "Add to Cart" button
7. HANDLE any post-add prompts (warranty, related products, etc.)
8. VERIFY product was added to cart successfully
9. TAKE screenshot showing cart confirmation

PRODUCT URL: {product_url}
QUANTITY: {quantity}
"""
        elif action == "view_cart":
            task = base_task + """
3. NAVIGATE to the shopping cart page
4. EXTRACT current cart contents:
   - List all items in cart with names, quantities, prices
   - Calculate subtotal and total
   - Note shipping information
   - Check for any cart warnings or issues
5. TAKE screenshot showing full cart contents

CART ANALYSIS:
- Item details and quantities
- Individual and total pricing
- Shipping options and costs
- Any promotional discounts
"""
        elif action == "update_quantity":
            task = base_task + f"""
3. NAVIGATE to the shopping cart page
4. LOCATE the specified product in cart
5. UPDATE quantity to {quantity}
6. APPLY the quantity change
7. VERIFY the cart total updates correctly
8. TAKE screenshot showing updated cart

TARGET QUANTITY: {quantity}
"""
        elif action == "remove_item":
            task = base_task + """
3. NAVIGATE to the shopping cart page
4. LOCATE the specified product in cart
5. REMOVE the item from cart
6. VERIFY the item is removed and cart updates
7. TAKE screenshot showing updated cart contents
"""

        task += f"""

CREDENTIALS:
- Username/Email: {credentials.get('username', 'N/A')}
- Password: [PROVIDED]

IMPORTANT REQUIREMENTS:
- Handle Amazon login process carefully
- Deal with any two-factor authentication prompts
- Navigate Amazon's dynamic cart interface
- Handle cart-specific promotions and suggestions
- Verify all changes take effect correctly
- Take clear screenshots showing results

SUCCESS CRITERIA:
- Successfully logged into Amazon
- Cart action completed as requested
- Changes verified and confirmed
- Clear screenshots documenting the process

ERROR HANDLING:
- Handle login issues (incorrect credentials, 2FA, captcha)
- Manage out-of-stock or unavailable products
- Deal with cart quantity limits
- Handle Amazon's security measures appropriately
"""

        return task.strip()

    async def _process_cart_result(self, agent_result: dict[str, Any],
                                 action: str, product_url: str | None) -> dict[str, Any]:
        """Process Claude agent result for cart management."""

        status = agent_result.get("status", "failed")
        claude_message = agent_result.get("message", "No message provided")
        screenshots = agent_result.get("screenshots", [])
        evidence = agent_result.get("evidence", {})

        result_data = {
            "cart_action": action,
            "product_url": product_url,
            "cart_contents": evidence.get("cart_items", []),
            "cart_subtotal": evidence.get("subtotal"),
            "cart_total": evidence.get("total"),
            "currency": evidence.get("currency", "USD"),
            "shipping_info": evidence.get("shipping_info", {}),
            "promotions": evidence.get("promotions", []),
            "action_completed": status == "success",
            "timestamp": time.time(),
            "iterations": agent_result.get("iterations", 0)
        }

        # Determine success message
        action_messages = {
            "add_product": f"Product {'added to' if status == 'success' else 'failed to add to'} cart",
            "view_cart": f"Cart contents {'retrieved' if status == 'success' else 'could not be retrieved'}",
            "update_quantity": f"Cart quantity {'updated' if status == 'success' else 'could not be updated'}",
            "remove_item": f"Item {'removed from' if status == 'success' else 'could not be removed from'} cart"
        }

        success_message = action_messages.get(action, f"Cart action {action} {'completed' if status == 'success' else 'failed'}")

        if status != "success":
            success_message += f": {claude_message}"

        # Get final screenshot
        final_screenshot = None
        if screenshots:
            final_screenshot = screenshots[-1].get("image_b64") if screenshots[-1] else None

        if not final_screenshot:
            final_screenshot = await self.capture_screenshot()

        return {
            "status": status,
            "message": success_message,
            "data": result_data,
            "screenshot": final_screenshot,
            "timestamp": time.time(),
            "execution_details": {
                "screenshots_captured": len(screenshots),
                "claude_response": claude_message,
                "session_id": self.session_id
            }
        }
