// ===================== COLLAPSIBLE SECTIONS =====================
const Sections = (() => {
    function collapsible() {
        document.querySelectorAll('.collapsible-section').forEach(section => {
            const header = section.querySelector('h3');
            if (!header) return;

            let icon = header.querySelector('.material-icons');
            if (!icon) {
                icon = document.createElement('span');
                icon.className = 'material-icons transition-transform duration-200 ml-2 rotate-0';
                icon.textContent = 'expand_more';
                header.appendChild(icon);
            } else {
                icon.classList.add('transition-transform', 'duration-200', 'ml-2');
                icon.classList.add('rotate-0');
            }

            const id = section.id;
            const collapsed = localStorage.getItem('collapse_' + id) === 'closed';
            icon.classList.toggle('rotate-180', !collapsed);
            icon.classList.toggle('rotate-0', collapsed);
            header.classList.toggle('mb-4', !collapsed);

            [...section.children].forEach(child => {
                if (child !== header && !child.classList.contains('force-hidden')) {
                    child.classList.toggle('hidden', collapsed);
                }
            });

            header.addEventListener('click', () => {
                const collapsed = section.classList.toggle('collapsed');
                [...section.children].forEach(child => { if (child !== header) child.classList.toggle('hidden', collapsed); });
                icon.classList.toggle('rotate-180', !collapsed);
                icon.classList.toggle('rotate-0', collapsed);
                header.classList.toggle('mb-4', !collapsed);
                localStorage.setItem('collapse_' + id, collapsed ? 'closed' : 'open');
            });
        });
    }

    return {collapsible};
})();


