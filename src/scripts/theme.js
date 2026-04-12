const themeToggle = document.getElementById('theme-toggle');
const html = document.documentElement;

// Check local storage or system preference
const getPreferredTheme = () => {
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme) {
    return savedTheme;
  }
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
};

// Set theme
const setTheme = (theme) => {
  html.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
};

// Initialize
setTheme(getPreferredTheme());

// Listen for toggle click
if (themeToggle) {
  themeToggle.addEventListener('click', () => {
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
  });
}

// Listen for system changes
window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', (e) => {
  if (!localStorage.getItem('theme')) {
    setTheme(e.matches ? 'light' : 'dark');
  }
});
