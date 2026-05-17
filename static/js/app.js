document.addEventListener("DOMContentLoaded", function () {
    const disabledLinks = document.querySelectorAll(".disabled-link");

    disabledLinks.forEach(function (link) {
        link.addEventListener("click", function (event) {
            event.preventDefault();
        });
    });
});