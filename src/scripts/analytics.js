// Custom Umami Analytics Tracking - Scroll Depth
// Clicking tracking is handled automatically by Umami via data-umami-event attributes

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
