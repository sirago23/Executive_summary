(function () {
  var root = document.documentElement;
  root.className += " js";

  var slides = Array.prototype.slice.call(document.querySelectorAll(".slide"));
  var count = document.getElementById("count");
  var toc = document.querySelector(".toc");
  var current = 0;

  function read(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (e) {
      return null;
    }
  }

  function write(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (e) {
      /* storage can be blocked; the deck still works without it */
    }
  }

  function show(index) {
    if (!slides.length) {
      return;
    }
    current = Math.max(0, Math.min(slides.length - 1, index));
    slides.forEach(function (slide, i) {
      slide.classList.toggle("active", i === current);
    });
    count.textContent = "Slide " + (current + 1) + " of " + slides.length;
    document.getElementById("prev").disabled = current === 0;
    document.getElementById("next").disabled = current === slides.length - 1;
    window.scrollTo(0, 0);
  }

  function showFromHash() {
    var id = window.location.hash.replace("#", "");
    for (var i = 0; i < slides.length; i++) {
      if (slides[i].id === id) {
        show(i);
        return;
      }
    }
    show(0);
  }

  document.getElementById("prev").addEventListener("click", function () {
    show(current - 1);
  });
  document.getElementById("next").addEventListener("click", function () {
    show(current + 1);
  });

  toc.addEventListener("click", function (event) {
    if (event.target.tagName === "A") {
      toc.removeAttribute("open");
    }
  });

  window.addEventListener("hashchange", showFromHash);

  document.addEventListener("keydown", function (event) {
    var tag = event.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || event.altKey || event.ctrlKey || event.metaKey) {
      return;
    }
    if (event.key === "ArrowRight" || event.key === "PageDown") {
      show(current + 1);
    } else if (event.key === "ArrowLeft" || event.key === "PageUp") {
      show(current - 1);
    } else if (event.key === "Home") {
      show(0);
    } else if (event.key === "End") {
      show(slides.length - 1);
    }
  });

  var themeKey = "exec-summary:theme";
  var savedTheme = read(themeKey);
  if (savedTheme === "light" || savedTheme === "dark") {
    root.setAttribute("data-theme", savedTheme);
  }
  document.getElementById("theme").addEventListener("click", function () {
    var explicit = root.getAttribute("data-theme");
    var systemDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    var isDark = explicit ? explicit === "dark" : systemDark;
    var next = isDark ? "light" : "dark";
    root.setAttribute("data-theme", next);
    write(themeKey, next);
  });

  var boxes = document.querySelectorAll("input[data-key]");
  Array.prototype.forEach.call(boxes, function (box) {
    box.checked = read(box.getAttribute("data-key")) === "1";
    box.addEventListener("change", function () {
      write(box.getAttribute("data-key"), box.checked ? "1" : "0");
    });
  });

  showFromHash();
})();
