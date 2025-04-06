declare global {
  interface Window {
    Telegram: {
      WebApp: {
        ready: () => void;
        expand: () => void;
        close: () => void;
        MainButton: {
          text: string;
          show: () => void;
          hide: () => void;
          onClick: (callback: () => void) => void;
        };
        BackButton: {
          show: () => void;
          hide: () => void;
          onClick: (callback: () => void) => void;
        };
        themeParams: {
          bg_color: string;
          text_color: string;
          hint_color: string;
          link_color: string;
          button_color: string;
          button_text_color: string;
        };
      };
    };
  }
}

// Check if running in Telegram Web App context
export const isTelegramWebApp = () => {
  return window.Telegram?.WebApp !== undefined;
};

// Export the WebApp instance if available
export const WebApp = isTelegramWebApp() ? window.Telegram.WebApp : null;

// Helper functions that check context before executing
export const showMainButton = (text: string, callback: () => void) => {
  if (WebApp?.MainButton) {
    WebApp.MainButton.text = text;
    WebApp.MainButton.onClick(callback);
    WebApp.MainButton.show();
  }
};

export const hideMainButton = () => {
  WebApp?.MainButton?.hide();
};

export const showBackButton = (callback: () => void) => {
  if (WebApp?.BackButton) {
    WebApp.BackButton.onClick(callback);
    WebApp.BackButton.show();
  }
};

export const hideBackButton = () => {
  WebApp?.BackButton?.hide();
};

export const getThemeParams = () => WebApp?.themeParams;

export const closeApp = () => WebApp?.close();

// Hook for Telegram context
export const useTelegramContext = () => {
  return {
    isInTelegram: isTelegramWebApp(),
    themeParams: getThemeParams(),
    showMainButton,
    hideMainButton,
    showBackButton,
    hideBackButton,
    closeApp
  };
};
