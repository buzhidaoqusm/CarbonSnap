import containerQueries from "@tailwindcss/container-queries";
import forms from "@tailwindcss/forms";

// Tailwind used to be compiled in the browser by cdn.tailwindcss.com, which kept
// the whole site blank whenever that host hung. It is now compiled at build time,
// with the version and plugins the CDN served (pinned in package.json).
//
// This is the config the CDN actually ran with: Tailwind's default. index.html
// also set a theme (custom colours and fonts, darkMode: "class"), but it did so
// before the CDN script loaded, the script replaced window.tailwind, and that
// theme never applied. Classes such as bg-primary or font-headline have never
// had any CSS; the pages that use them get rebuilt in the redesign.
export default {
  // Only classes written out in full in these files get CSS: a class name put
  // together at runtime has none.
  content: {
    relative: true,
    files: ["./index.html", "./src/**/*.{vue,js}"],
  },
  plugins: [forms, containerQueries],
};
