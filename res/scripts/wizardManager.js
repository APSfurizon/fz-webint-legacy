function initObjects (){
    draggables = document.querySelectorAll("div.grid.people div.edit-drag");
    rooms = document.querySelectorAll("main.container>div.room");
    Array.from(draggables).forEach(element => {
        element.addEventListener('dragstart', dragStart);
        element.addEventListener('dragend', dragEnd);
    });
    Array.from(rooms).forEach(room => {
        room.addEventListener('dragenter', dragEnter)
        room.addEventListener('dragover', dragOver);
        room.addEventListener('dragleave', dragLeave);
        room.addEventListener('drop', drop);
    });
}

function dragStart(e) {
    element = e.target;
    room = element.closest('div.room')
    dataToSave = {
        id: element.id,
        type: element.getAttribute('room-type'),
        parentId: room.id
    }
    e.dataTransfer.setData('application/json', JSON.stringify(dataToSave));
    toggleRoomSelection(true);
}

function dragEnd(e) {
    toggleRoomSelection(false);
    e.stopPropagation();
}

function dragEnter(e) {
    e.preventDefault();
    e.target.classList.add('drag-over');
    checkDragLocation (decodeData(e), e.target);
    e.stopPropagation();
}

function dragOver(e) {
    e.preventDefault();
    e.target.classList.add('drag-over');
    checkDragLocation (decodeData(e), e.target);
    e.stopPropagation();
}

/**
 * @param {DragEvent} e 
 * @returns 
 */
function decodeData (e) {
    const raw = e.dataTransfer.getData('application/json');
    console.log(raw);
    return JSON.parse(raw);
}

/**
 * 
 * @param {Element} target 
 */
function checkDragLocation (data, target) {
    let toReturn = true;
    const isInfinite = target.getAttribute("infinite");
    const maxSizeReached = target.getAttribute("current-size") >= target.getAttribute("room-size");
    const roomTypeMismatch = data.type !== target.getAttribute("room-type");
    if (!isInfinite && (maxSizeReached || roomTypeMismatch)) {
        target.classList.add('drag-forbidden');
        toReturn = false;
    }
    return toReturn;
}

function dragLeave(e) {
    e.target.classList.remove('drag-over');
    e.target.classList.remove('drag-forbidden');
}

function drop(e) {
    e.target.classList.remove('drag-over');
    toggleRoomSelection(false);
    if (checkDragLocation(decodeData(e), e.target) === true) {
        console.log ()
        const data = decodeData (e);
        let item = document.getElementById (data.id)
        let oldParent = document.getElementById (data.parentId)
        let newParent = e.target;
        let newParentContainer = newParent.querySelector('div.grid.people')
        newParentContainer.appendChild (item);
        oldParent.setAttribute("current-size", parseInt(oldParent.getAttribute("current-size") - 1))
        newParent.setAttribute("current-size", parseInt(newParent.getAttribute("current-size") + 1))
    }
}

function toggleRoomSelection(newStatus) {
    rooms = document.querySelectorAll("main.container>div.room");
    Array.from(rooms).forEach(room=>{
        room.classList.toggle('interactless', newStatus);
        room.classList.remove('drag-over');
        room.classList.remove('drag-forbidden');
    })
}

initObjects ();