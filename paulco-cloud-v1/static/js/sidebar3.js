const hamBurger = document.querySelector(".toggle-btn");

hamBurger.addEventListener("click", function () {
  document.querySelector("#sidebar").classList.toggle("expand");
});

document.querySelectorAll('.sidebar-parent').forEach(function(parent) {
  parent.addEventListener('click', function(e) {
    e.preventDefault();
    var target = document.querySelector(parent.getAttribute('data-bs-target'));
    if (target.classList.contains('show')) {
      target.classList.remove('show');
      parent.setAttribute('aria-expanded', 'false');
    } else {
      // Optionally close other open submenus
      document.querySelectorAll('.sidebar-subnav.show').forEach(function(open) {
        open.classList.remove('show');
      });
      target.classList.add('show');
      parent.setAttribute('aria-expanded', 'true');
    }
  });
});
