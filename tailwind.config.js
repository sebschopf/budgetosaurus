/** @type {import('tailwindcss').Config} */
module.exports = {
  // Le chemin vers tous les fichiers qui pourraient contenir des classes Tailwind.
  // Tailwind va scanner ces fichiers pour ne générer que le CSS que vous utilisez.
  content: [
    "./personal_budget/templates/**/*.html", // Pour les templates généraux de Django si vous en avez à la racine
    "./webapp/templates/**/*.html", // Pour les templates de votre application webapp
    "./webapp/static/webapp/js/**/*.js", // Pour les classes Tailwind utilisées dans vos fichiers JS
    // Vous pouvez ajouter d'autres chemins si vous avez des fichiers HTML/JS ailleurs
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
