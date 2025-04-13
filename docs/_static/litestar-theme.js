function initDropdowns() {
    const dropdownToggles = document.querySelectorAll(".st-dropdown-toggle")

    const dropdowns = [...dropdownToggles].map(toggleEl => ({
        toggleEl,
        contentEL: toggleEl.parentElement.querySelector(".st-dropdown-menu")
    }))

    const close = (dropdown) => {
        const {toggleEl, contentEL} = dropdown
        toggleEl.setAttribute("aria-expanded", "false")
        contentEL.classList.toggle("hidden", true)
    }

    const closeAll = () => dropdowns.forEach(close)

    const open = (dropdown) => {
        closeAll()
        dropdown.toggleEl.setAttribute("aria-expanded", "true")
        dropdown.contentEL.classList.toggle("hidden", false)
        const boundaries = [dropdown.contentEL, ...dropdownToggles]
        const clickOutsideListener = (event) => {
            const target = event.target
            if (!target) return

            if (!boundaries.some(b => b.contains(target))) {
                closeAll()
                document.removeEventListener("click", clickOutsideListener)
            }

        }
        document.addEventListener("click", clickOutsideListener)
    }


    dropdowns.forEach(dropdown => {
        dropdown.toggleEl.addEventListener("click", () => {
            if (dropdown.toggleEl.getAttribute("aria-expanded") === "true") {
                close(dropdown)
            } else {
                open(dropdown)
            }
        })
    })
}

window.addEventListener("DOMContentLoaded", () => {
    initDropdowns()
})
