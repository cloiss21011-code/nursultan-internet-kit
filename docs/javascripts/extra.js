/* Nursultan Internet Kit — вёрстка в духе docs.nursultan.fun */
(function () {
  "use strict";

  var mac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);

  /* подсказка клавиши в поиске: Ctrl или ⌘ */
  var mod = document.querySelector("[data-md-search-mod]");
  if (mod && mac) {
    mod.textContent = "\u2318";
  }

  /* горизонтальный скролл широких таблиц (как .table-scroll у оригинала) */
  document.querySelectorAll(".md-typeset table:not([class])").forEach(function (table) {
    var wrap = document.createElement("div");
    wrap.className = "table-scroll";
    table.parentNode.insertBefore(wrap, table);
    wrap.appendChild(table);
  });

  /* кнопка «Копировать» справа от заголовка страницы */
  var h1 = document.querySelector(".md-typeset h1");
  if (!h1) {
    return;
  }

  function flash(el, text) {
    var span = el.querySelector("span");
    if (!span) {
      return;
    }
    var old = span.textContent;
    span.textContent = text;
    window.setTimeout(function () {
      span.textContent = old;
    }, 1500);
  }

  function copyText(value, button) {
    if (!navigator.clipboard) {
      return;
    }
    navigator.clipboard.writeText(value).then(function () {
      flash(button, "Скопировано");
    });
  }

  var box = document.createElement("div");
  box.className = "kit-page-actions";

  var main = document.createElement("button");
  main.type = "button";
  main.className = "kit-page-actions__main";
  main.innerHTML =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"></rect><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c0 1.1.9 2 2 2"></path></svg>' +
    "<span>Копировать</span>";
  main.addEventListener("click", function () {
    var article = document.querySelector(".md-typeset");
    var text = article ? article.innerText : document.body.innerText;
    copyText(text + "\n" + location.href, main);
  });

  var more = document.createElement("button");
  more.type = "button";
  more.className = "kit-page-actions__more";
  more.setAttribute("aria-label", "Ещё");
  more.innerHTML =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"></path></svg>';

  var menu = document.createElement("div");
  menu.className = "kit-page-actions__menu";
  var linkItem = document.createElement("button");
  linkItem.type = "button";
  linkItem.innerHTML = "<span>Ссылка на страницу</span>";
  linkItem.addEventListener("click", function () {
    if (!navigator.clipboard) {
      return;
    }
    navigator.clipboard.writeText(location.href).then(function () {
      menu.classList.remove("is-open");
    });
  });
  menu.appendChild(linkItem);
  more.addEventListener("click", function (event) {
    event.stopPropagation();
    menu.classList.toggle("is-open");
  });
  document.addEventListener("click", function () {
    menu.classList.remove("is-open");
  });

  box.appendChild(main);
  box.appendChild(more);
  box.appendChild(menu);
  h1.parentNode.insertBefore(box, h1);
})();
