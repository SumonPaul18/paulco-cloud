document.addEventListener('DOMContentLoaded', function () {
    var sidebarItems = document.querySelectorAll('.sidebar-item.has-dropdown');

    sidebarItems.forEach(function (item) {
        item.addEventListener('click', function () {
            var target = item.querySelector('.sidebar-dropdown');
            var isExpanded = item.getAttribute('aria-expanded') === 'true';
            item.setAttribute('aria-expanded', !isExpanded);
            target.classList.toggle('collapse', isExpanded);
        });
    });
});