(() => {
  "use strict";

  const translations = new Map(Object.entries({
    "All applications": "Все приложения",
    "Article likes": "Отметки «нравится» у статей",
    "Axes": "Безопасность входа",
    "Blacklisted tokens": "Заблокированные токены",
    "Blog series visits": "Посещения серий статей",
    "Community post bookmarks": "Закладки сообщества",
    "Community post comments": "Комментарии сообщества",
    "Community post dislikes": "Отметки «не нравится»",
    "Community post reposts": "Репосты сообщества",
    "Dark": "Тёмная",
    "Light": "Светлая",
    "Menu": "Меню",
    "Outstanding tokens": "Активные токены",
    "Pages": "Страницы",
    "Review comments": "Комментарии к отзывам",
    "Run": "Выполнить",
    "Search": "Поиск",
    "Search apps and models...": "Поиск приложений и моделей...",
    "Select action": "Выберите действие",
    "Select action to run": "Выберите действие для выполнения",
    "Select all rows": "Выбрать все строки",
    "Select record": "Выберите запись",
    "System": "Системная",
    "Token Blacklist": "Токены доступа",
    "Type to search": "Начните вводить для поиска",
    "User Agent": "Браузер и устройство",
    "HTTP Accept": "Заголовок HTTP Accept",
    "Session key hash (sha256)": "Хеш ключа сессии (SHA-256)",
    "Settings": "Настройки",
    "settings": "настройки",
    "App": "Приложение",
    "app": "приложение",
    "Account": "Учётная запись",
    "account": "учётная запись",
    "Created at": "Создано",
    "created at": "создано",
    "Updated at": "Обновлено",
    "updated at": "обновлено",
    "Expires at": "Истекает",
    "expires at": "истекает",
    "Blacklisted at": "Заблокирован",
    "blacklisted at": "заблокирован",
    "Token": "Токен",
    "token": "токен",
    "Post": "Запись",
    "post": "запись",
    "Parent": "Родительский комментарий",
    "parent": "родительский комментарий",
    "Text": "Текст",
    "text": "текст",
    "User": "Пользователь",
    "user": "пользователь",
    "Slug": "Адрес в URL",
    "slug": "адрес в URL"
  }));

  const translateValue = (value) => {
    if (!value) return value;
    const key = value.trim();
    const translated = translations.get(key);
    if (!translated) return value;
    return value.replace(key, translated);
  };

  const translateTextNode = (node) => {
    const current = node.nodeValue;
    const translated = translateValue(current);
    if (translated !== current) {
      node.nodeValue = translated;
    }
  };

  const translateAttribute = (element, attribute) => {
    const current = element.getAttribute(attribute);
    const translated = translateValue(current);
    if (translated !== current) {
      element.setAttribute(attribute, translated);
    }
  };

  const translateTree = (root) => {
    if (!root) return;
    if (root.nodeType === Node.TEXT_NODE) {
      translateTextNode(root);
      return;
    }
    if (root.nodeType !== Node.ELEMENT_NODE && root.nodeType !== Node.DOCUMENT_NODE) return;

    if (root.nodeType === Node.ELEMENT_NODE) {
      ["placeholder", "title", "aria-label"].forEach((attribute) => {
        if (root.hasAttribute(attribute)) {
          translateAttribute(root, attribute);
        }
      });
    }

    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      translateTextNode(node);
    }
    if (root.querySelectorAll) {
      root.querySelectorAll("[placeholder], [title], [aria-label]").forEach((element) => {
        ["placeholder", "title", "aria-label"].forEach((attribute) => {
          if (element.hasAttribute(attribute)) {
            translateAttribute(element, attribute);
          }
        });
      });
    }
  };

  const start = () => {
    translateTree(document.body);
    new MutationObserver((records) => {
      records.forEach((record) => {
        record.addedNodes.forEach(translateTree);
        if (record.type === "characterData") translateTree(record.target);
      });
    }).observe(document.body, { childList: true, subtree: true, characterData: true });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
