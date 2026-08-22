// Custom analytics tracking - scroll depth and interaction events.

if (typeof window !== 'undefined') {
  const trackedDepths = new Set();

  const handleScroll = () => {
    const scrollHeight = document.documentElement.scrollHeight;
    const windowHeight = window.innerHeight;
    const scrollTop = window.scrollY || document.documentElement.scrollTop;

    // Calculate percentage, maxing out at 100
    let depth = Math.round(((scrollTop + windowHeight) / scrollHeight) * 100);

    // Avoid tracking over 100% on iOS bounce
    if (depth > 100) depth = 100;

    const milestones = [25, 50, 75, 100];

    for (const milestone of milestones) {
      if (depth >= milestone && !trackedDepths.has(milestone)) {
        if (window.umami && typeof window.umami.track === 'function') {
          trackedDepths.add(milestone);
          window.umami.track(`scroll-${milestone}`);
        }
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

  // Track button clicks for Google Tag (gtag.js) and backup triggers
  const interactiveElements = document.querySelectorAll('[data-umami-event]');
  interactiveElements.forEach((element) => {
    element.addEventListener('click', () => {
      const eventName = element.getAttribute('data-umami-event');
      if (eventName && typeof window.gtag === 'function') {
        window.gtag('event', eventName, {
          event_category: 'interaction',
          event_label: eventName.replace('click-', '').replace('download-', ''),
        });

        // Google Ads Conversion tracking for Google Calendar book a call button
        if (eventName === 'click-gcal') {
          window.gtag('event', 'conversion', {
            send_to: 'AW-962696895/ZM9VCJjNyL4cEL-thssD',
          });
        }
      }
    });
  });
}
