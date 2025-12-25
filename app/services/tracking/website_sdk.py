"""Website event tracking SDK - JavaScript code generation and event processing."""

from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID
import hashlib
import json


class WebsiteTrackingSDK:
    """Generates and manages website tracking SDK."""

    def generate_tracking_script(
        self,
        tenant_uuid: UUID,
        tracking_domain: str = "track.engarde.com",
    ) -> str:
        """
        Generate JavaScript tracking code for website.

        Args:
            tenant_uuid: Tenant UUID for tracking
            tracking_domain: Tracking endpoint domain

        Returns:
            JavaScript tracking code
        """
        script = f"""
<!-- Madan Sara Website Tracking -->
<script>
(function() {{
    window.MadanSara = window.MadanSara || {{}};

    var config = {{
        tenantId: '{tenant_uuid}',
        endpoint: 'https://{tracking_domain}/api/v1/website/track',
        autoTrack: true,
        trackPageViews: true,
        trackClicks: true,
        trackFormSubmits: true,
        sessionTimeout: 1800000 // 30 minutes
    }};

    // Generate visitor ID (cookie-based)
    function getVisitorId() {{
        var visitorId = getCookie('ms_visitor_id');
        if (!visitorId) {{
            visitorId = generateUUID();
            setCookie('ms_visitor_id', visitorId, 365);
        }}
        return visitorId;
    }}

    // Generate session ID
    function getSessionId() {{
        var sessionId = sessionStorage.getItem('ms_session_id');
        var lastActivity = sessionStorage.getItem('ms_last_activity');
        var now = Date.now();

        if (!sessionId || !lastActivity || (now - parseInt(lastActivity)) > config.sessionTimeout) {{
            sessionId = generateUUID();
            sessionStorage.setItem('ms_session_id', sessionId);
        }}

        sessionStorage.setItem('ms_last_activity', now.toString());
        return sessionId;
    }}

    // Track event
    function track(eventType, eventData) {{
        var payload = {{
            tenant_uuid: config.tenantId,
            visitor_id: getVisitorId(),
            session_id: getSessionId(),
            event_type: eventType,
            event_data: eventData,
            page_url: window.location.href,
            page_title: document.title,
            referrer: document.referrer,
            timestamp: new Date().toISOString(),
            user_agent: navigator.userAgent,
            screen_resolution: screen.width + 'x' + screen.height,
            viewport_size: window.innerWidth + 'x' + window.innerHeight
        }};

        // Send to tracking endpoint
        if (navigator.sendBeacon) {{
            navigator.sendBeacon(
                config.endpoint,
                new Blob([JSON.stringify(payload)], {{ type: 'application/json' }})
            );
        }} else {{
            fetch(config.endpoint, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(payload),
                keepalive: true
            }}).catch(function(err) {{
                console.error('Tracking failed:', err);
            }});
        }}
    }}

    // Auto-track page view
    if (config.trackPageViews) {{
        track('page_view', {{
            path: window.location.pathname,
            search: window.location.search,
            hash: window.location.hash
        }});
    }}

    // Auto-track clicks
    if (config.trackClicks) {{
        document.addEventListener('click', function(e) {{
            var target = e.target;
            var tagName = target.tagName.toLowerCase();

            if (tagName === 'a' || tagName === 'button') {{
                track('click', {{
                    element_type: tagName,
                    element_id: target.id,
                    element_class: target.className,
                    element_text: target.textContent.trim().substring(0, 100),
                    href: target.href || null
                }});
            }}
        }});
    }}

    // Auto-track form submissions
    if (config.trackFormSubmits) {{
        document.addEventListener('submit', function(e) {{
            var form = e.target;
            track('form_submit', {{
                form_id: form.id,
                form_action: form.action,
                form_method: form.method
            }});
        }});
    }}

    // Track scroll depth
    var maxScrollDepth = 0;
    window.addEventListener('scroll', debounce(function() {{
        var scrollDepth = Math.round(
            (window.scrollY / (document.documentElement.scrollHeight - window.innerHeight)) * 100
        );

        if (scrollDepth > maxScrollDepth) {{
            maxScrollDepth = scrollDepth;

            // Track milestones (25%, 50%, 75%, 100%)
            if ([25, 50, 75, 100].includes(scrollDepth)) {{
                track('scroll_depth', {{
                    depth: scrollDepth,
                    page: window.location.pathname
                }});
            }}
        }}
    }}, 1000));

    // Expose API
    window.MadanSara.track = track;
    window.MadanSara.getVisitorId = getVisitorId;
    window.MadanSara.getSessionId = getSessionId;

    // Helper functions
    function generateUUID() {{
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {{
            var r = Math.random() * 16 | 0;
            var v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        }});
    }}

    function getCookie(name) {{
        var match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
        return match ? match[2] : null;
    }}

    function setCookie(name, value, days) {{
        var expires = new Date();
        expires.setTime(expires.getTime() + days * 24 * 60 * 60 * 1000);
        document.cookie = name + '=' + value + ';expires=' + expires.toUTCString() + ';path=/';
    }}

    function debounce(func, wait) {{
        var timeout;
        return function() {{
            var context = this, args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(function() {{
                func.apply(context, args);
            }}, wait);
        }};
    }}
}})();
</script>
"""
        return script.strip()

    async def process_tracking_event(
        self,
        event_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Process incoming tracking event from website.

        Args:
            event_data: Event data from JavaScript SDK

        Returns:
            Processing result
        """
        try:
            # Extract key fields
            tenant_uuid = event_data.get("tenant_uuid")
            visitor_id = event_data.get("visitor_id")
            session_id = event_data.get("session_id")
            event_type = event_data.get("event_type")
            timestamp = event_data.get("timestamp")

            # Validate required fields
            if not all([tenant_uuid, visitor_id, session_id, event_type]):
                return {
                    "success": False,
                    "error": "Missing required fields"
                }

            # TODO: Store event in database
            # - Update WebsiteVisitor
            # - Update/create WebsiteSession
            # - Create PageView or WebsiteEvent record

            # Detect customer type (new, returning, existing)
            customer_type = await self._detect_customer_type(tenant_uuid, visitor_id)

            # Calculate funnel stage if applicable
            funnel_stage = self._detect_funnel_stage(event_data.get("page_url", ""))

            return {
                "success": True,
                "visitor_id": visitor_id,
                "session_id": session_id,
                "customer_type": customer_type,
                "funnel_stage": funnel_stage,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def _detect_customer_type(
        self,
        tenant_uuid: str,
        visitor_id: str,
    ) -> str:
        """
        Detect if visitor is new, returning, or existing customer.

        Args:
            tenant_uuid: Tenant UUID
            visitor_id: Visitor ID

        Returns:
            Customer type: new, returning, or existing
        """
        # TODO: Query database
        # - Check if visitor exists
        # - Check if they have previous sessions
        # - Check if they're a customer (has conversions)

        # For now, return placeholder
        return "new"

    def _detect_funnel_stage(
        self,
        page_url: str,
    ) -> Optional[str]:
        """
        Detect funnel stage from page URL.

        Args:
            page_url: Current page URL

        Returns:
            Funnel stage or None
        """
        # Common funnel stage patterns
        if "/product" in page_url or "/item" in page_url:
            return "product"
        elif "/cart" in page_url:
            return "cart"
        elif "/checkout" in page_url:
            return "checkout"
        elif "/thank" in page_url or "/confirmation" in page_url:
            return "conversion"
        elif "/" == page_url or "/home" in page_url:
            return "homepage"
        else:
            return "browsing"

    def generate_ab_test_script(
        self,
        test_id: UUID,
        variants: List[Dict[str, Any]],
    ) -> str:
        """
        Generate A/B test JavaScript code.

        Args:
            test_id: A/B test ID
            variants: List of test variants

        Returns:
            JavaScript code for A/B test
        """
        variants_json = json.dumps(variants)

        script = f"""
<script>
(function() {{
    var testId = '{test_id}';
    var variants = {variants_json};

    // Get or assign variant
    function getVariant() {{
        var storageKey = 'ms_ab_test_' + testId;
        var assignedVariant = localStorage.getItem(storageKey);

        if (!assignedVariant) {{
            // Random assignment based on traffic allocation
            var rand = Math.random();
            var cumulative = 0;

            for (var i = 0; i < variants.length; i++) {{
                cumulative += variants[i].traffic_percentage;
                if (rand <= cumulative) {{
                    assignedVariant = variants[i].id;
                    break;
                }}
            }}

            localStorage.setItem(storageKey, assignedVariant);

            // Track assignment
            if (window.MadanSara && window.MadanSara.track) {{
                window.MadanSara.track('ab_test_assigned', {{
                    test_id: testId,
                    variant_id: assignedVariant
                }});
            }}
        }}

        return assignedVariant;
    }}

    // Apply variant
    function applyVariant(variantId) {{
        var variant = variants.find(function(v) {{ return v.id === variantId; }});
        if (!variant) return;

        var config = variant.config;

        // Apply button changes
        if (config.button_text) {{
            var buttons = document.querySelectorAll(config.button_selector || '.cta-button');
            buttons.forEach(function(btn) {{
                btn.textContent = config.button_text;
                if (config.button_color) btn.style.backgroundColor = config.button_color;
                if (config.button_size) btn.style.fontSize = config.button_size;
            }});
        }}

        // Apply copy changes
        if (config.headline) {{
            var headline = document.querySelector(config.headline_selector || 'h1');
            if (headline) headline.textContent = config.headline;
        }}
    }}

    // Execute on page load
    window.addEventListener('DOMContentLoaded', function() {{
        var variantId = getVariant();
        applyVariant(variantId);
    }});
}})();
</script>
"""
        return script.strip()
