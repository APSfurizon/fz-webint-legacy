function confirmAction (intent, sender) {
    if (['rename', 'unconfirm', 'delete'].includes (intent) == false) return
    let href = sender.getAttribute('action')
    let intentTitle = document.querySelector("#modalOrderEditDialog #intentText")
    let intentEdit =  document.querySelector("#modalOrderEditDialog #intentRename")
    let intentEditPanel =  document.querySelector("#modalOrderEditDialog #intentEditPanel")
    let intentFormAction =  document.querySelector("#intentFormAction")
    let intentSend =  document.querySelector("#modalOrderEditDialog #intentSend")
    // Resetting ui
    intentEdit.removeAttribute('required')
    intentEdit.removeAttribute('minlength')
    intentFormAction.setAttribute('method', 'GET')
    intentEditPanel.style.display = 'none';

    intentTitle.innerText = intent + ' room'
    intentFormAction.setAttribute('action', href)
    switch (intent){
        case 'rename':
            intentEditPanel.style.display = 'block';
            intentEdit.setAttribute('required', true)
            intentEdit.setAttribute('minlength', 4)
            intentFormAction.setAttribute('method', 'POST')
            document.getElementById("intentRename").value = sender.parentElement.parentElement.querySelector("span").innerText;
            break
        case 'unconfirm':
            break
        case 'delete':
            break
    }
    document.getElementById('modalOrderEditDialog').setAttribute('open', 'true');
}

function setLoading (){
    document.getElementById('loadingIndicator').style.visibility = 'unset';
}

function setLoaded (){
    document.getElementById('loadingIndicator').style.visibility = 'hidden';
}

async function roomGuestEditAction (intent, sender) {
    if (['new', 'fromOrder'].includes (intent) == false) return
    setLoaded ();
    document.getElementById('roomGuestEditorDialog').setAttribute('open', 'true');
}

async function retrieveUsers (type) {
    setLoading();

    setLoaded();
}

function adaptRoomFormat (){
    
}