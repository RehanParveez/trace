import i18n from "i18next";
import { initReactI18next } from "react-i18next";

void i18n.use(initReactI18next).init({
  lng: "en",
  fallbackLng: "en",
  resources: {
    en: {
      translation: {
        appName: "Trace",
        tagline: "Construction Intelligence Platform",
      },
    },
    ur: {
      translation: {
        appName: "Trace",
        tagline: "تعمیراتی معلوماتی پلیٹ فارم",
      },
    },
  },
});

export default i18n;
