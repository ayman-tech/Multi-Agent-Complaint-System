// Dark/light theme toggle — persists preference in localStorage
(function() {
  const saved = localStorage.getItem('theme');
  if (saved === 'light') {
    document.documentElement.classList.remove('dark');
  }
})();

function toggleTheme() {
  const html = document.documentElement;
  html.classList.toggle('dark');
  localStorage.setItem('theme', html.classList.contains('dark') ? 'dark' : 'light');
}
