// Custom analytics tracking - scroll depth.
// Click tracking is handled by the Umami-compatible Cloudflare shim via data-umami-event attributes.

if (typeof window !== 'undefined' && window.umami) {
  let trackedDepths = new Set();
  
  const handleScroll = () => {
    const scrollHeight = document.documentElement.scrollHeight;
    const windowHeight = window.innerHeight;
    const scrollTop = window.scrollY || document.documentElement.scrollTop;
    
    // Calculate percentage, maxing out at 100
    let depth = Math.round((scrollTop + windowHeight) / scrollHeight * 100);
    
    // Avoid tracking over 100% on iOS bounce
    if (depth > 100) depth = 100;
    
    const milestones = [25, 50, 75, 100];
    
    for (const milestone of milestones) {
      if (depth >= milestone && !trackedDepths.has(milestone)) {
        trackedDepths.add(milestone);
        umami.track(`scroll-${milestone}`);
      }
    }
  };

  // Throttle the scroll event
  let ticking = false;
  window.addEventListener('scroll', () => {
    if (!ticking) {
      window.requestAnimationFrame(() => {
        handleScroll();
        ticking = false;
      });
      ticking = true;
    }
  });
}

// Track button clicks for Google Tag (gtag.js)
if (typeof window !== 'undefined') {
  const contactButtons = document.querySelectorAll('.links .link-btn');
  contactButtons.forEach(button => {
    button.addEventListener('click', () => {
      const eventName = button.getAttribute('data-umami-event');
      if (eventName && typeof window.gtag === 'function') {
        window.gtag('event', eventName, {
          event_category: 'contact',
          event_label: eventName.replace('click-', '')
        });
        
        // Google Ads Conversion tracking for Google Calendar book a call button
        if (eventName === 'click-gcal') {
          window.gtag('event', 'conversion', {
            'send_to': 'AW-962696895/ZM9VCJjNyL4cEL-thssD'
          });
        }
      }
    });
  });
}

