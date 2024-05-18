var draggingData = {
    id: 0,
    roomTypeId: 0,
    parentRoomId: 0
}

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

/**
 * 
 * @param {DragEvent} e 
 */
function dragStart(e) {
    element = e.target;
    room = element.closest('div.room')
    setData(element.id, element.getAttribute('room-type'), room.id)
    e.dataTransfer.effectAllowed = 'move';
    setTimeout(()=>toggleRoomSelection(true), 0);
}

function dragEnd(e) {
    toggleRoomSelection(false);
    resetData ();
    e.stopPropagation();
}

function dragEnter(e) {
    e.preventDefault();
    e.target.classList.add('drag-over');
    checkDragLocation (getData(), e.target);
    e.stopPropagation();
}

function dragOver(e) {
    e.preventDefault();
    e.target.classList.add('drag-over');
    checkDragLocation (getData(), e.target)
    e.stopPropagation();
}

/**
 * 
 * @param {Element} target 
 */
function checkDragLocation (data, target) {
    let toReturn = true;
    const isInfinite = target.getAttribute("infinite");
    const maxSizeReached = target.getAttribute("current-size") >= target.getAttribute("room-size");
    const roomTypeMismatch = data.roomTypeId !== target.getAttribute("room-type");
    if (!isInfinite && (maxSizeReached || roomTypeMismatch)) {
        target.classList.add('drag-forbidden');
        toReturn = false;
    } else {
        target.classList.remove('drag-forbidden');
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
    if (checkDragLocation(getData(), e.target) === true) {
        const data = getData();
        let item = document.getElementById (data.id)
        let oldParent = document.getElementById (data.parentRoomId)
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

function setData (id, roomType, parentRoomId) {
    draggingData.id = id;
    draggingData.roomTypeId = roomType;
    draggingData.parentRoomId = parentRoomId;
}

function resetData (){
    setData(0, 0, 0);
}

function getData () {
    return draggingData;
}

initObjects ();