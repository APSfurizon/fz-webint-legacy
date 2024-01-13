function onScrollNav () {
    if (Number(window.currentScroll) == 0) {
        window.currentScroll = window.scrollY || document.documentElement.scrollTop;
        return;
    }
    let newOffset = window.scrollY || document.documentElement.scrollTop;

    document.getElementById('topbar').classList.toggle('closed', newOffset > window.currentScroll);
    window.currentScroll = newOffset <= 0 ? 0 : newOffset;
}

document.getElementById('mobileMenu').addEventListener('click', function (e) {
    menuClick (e.target);
    e.stopPropagation();
});

function menuClick (e, force){
    let menuItem = e.closest('img');
    let isOpen = false;
    isOpen = document.querySelector('nav div.navbar-container').classList.toggle('open', force);
    
    menuItem.setAttribute('src', isOpen ? '/res/icons/close.svg' : '/res/icons/menu.svg');
}