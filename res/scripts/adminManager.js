function confirmAction (intent, sender) {
    if (['propicReminder'].includes (intent) == false) return
    let href = sender.getAttribute('action')
    let intentTitle = document.querySelector("#intentText")
    let intentDescription =  document.querySelector("#intentDescription")
    let intentEditPanel =  document.querySelector("#intentEditPanel")
    let intentFormAction =  document.querySelector("#intentFormAction")
    let intentSend =  document.querySelector("#intentSend")
    // Resetting ui
    intentFormAction.setAttribute('method', 'GET')
    intentEditPanel.style.display = 'none';
    intentDescription.innerText = sender.title;
    intentFormAction.setAttribute('action', href)
    switch (intent){
        case 'propicReminder':
            intentTitle.innerText = "Send missing badge reminders";
            intentSend.innerText = sender.innerText;
            break;
    }
    document.getElementById('modalRoomconfirm').setAttribute('open', 'true');
}