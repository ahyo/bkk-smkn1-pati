/* Interaksi ringan portal BKK — tanpa dependensi eksternal. */
(function () {
  "use strict";

  // Menu mobile
  var toggle = document.querySelector(".nav-toggle");
  var links = document.querySelector(".nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", function () {
      links.classList.toggle("open");
    });
  }

  // Dropdown akun
  document.querySelectorAll(".dropdown-toggle").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      var parent = btn.closest(".dropdown");
      document.querySelectorAll(".dropdown.open").forEach(function (d) {
        if (d !== parent) d.classList.remove("open");
      });
      parent.classList.toggle("open");
    });
  });
  document.addEventListener("click", function () {
    document.querySelectorAll(".dropdown.open").forEach(function (d) {
      d.classList.remove("open");
    });
  });

  // Menu dashboard yang dapat dilipat di layar sempit
  var sideToggle = document.querySelector(".sidebar-toggle");
  if (sideToggle) {
    sideToggle.addEventListener("click", function () {
      var side = sideToggle.closest(".sidebar");
      var buka = side.classList.toggle("open");
      sideToggle.setAttribute("aria-expanded", buka ? "true" : "false");
    });
  }

  // Konfirmasi aksi destruktif
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("submit", function (e) {
      if (!window.confirm(el.getAttribute("data-confirm"))) e.preventDefault();
    });
    el.addEventListener("click", function (e) {
      if (el.tagName !== "FORM" && !window.confirm(el.getAttribute("data-confirm"))) e.preventDefault();
    });
  });

  // Auto-submit filter saat select berubah
  document.querySelectorAll("[data-autosubmit]").forEach(function (el) {
    el.addEventListener("change", function () {
      el.closest("form").submit();
    });
  });

  // Tutup flash otomatis
  setTimeout(function () {
    document.querySelectorAll(".flash-wrap .alert").forEach(function (a) {
      a.style.transition = "opacity .4s";
      a.style.opacity = "0";
      setTimeout(function () { a.remove(); }, 400);
    });
  }, 6000);

  // Hitung karakter textarea dengan maxlength
  document.querySelectorAll("textarea[maxlength]").forEach(function (ta) {
    var counter = document.createElement("div");
    counter.className = "help right";
    ta.parentNode.appendChild(counter);
    var update = function () {
      counter.textContent = ta.value.length + " / " + ta.getAttribute("maxlength") + " karakter";
    };
    ta.addEventListener("input", update);
    update();
  });

  // Pratinjau nama berkas yang dipilih
  document.querySelectorAll('input[type="file"]').forEach(function (inp) {
    inp.addEventListener("change", function () {
      var hint = inp.parentNode.querySelector(".file-hint");
      if (hint && inp.files.length) hint.textContent = "Dipilih: " + inp.files[0].name;
    });
  });
})();
