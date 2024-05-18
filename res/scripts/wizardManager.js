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
        if (moveToRoom (data.id, data.parentRoomId.replace('room-',''), newParent.id.replace('room-','')) === true) {
            let newParentContainer = newParent.querySelector('div.grid.people')
            newParentContainer.appendChild (item);
            let oldParentQty = parseInt(oldParent.getAttribute("current-size")) - 1;
            let newParentQty = parseInt(newParent.getAttribute("current-size")) + 1;
            let newParentCapacity = parseInt(newParent.getAttribute("room-size"));
            oldParent.setAttribute("current-size", oldParentQty);
            newParent.setAttribute("current-size", newParentQty);
            oldParent.classList.remove('complete');
            if (newParentCapacity == newParentQty) newParent.classList.add('complete');
        }
    }
}

function toggleRoomSelection(newStatus) {
    rooms = document.querySelectorAll("div.room");
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

function resetData (){ setData(0, 0, 0); }

function getData () { return draggingData; }

// This default onbeforeunload event
window.onbeforeunload = function(){
    return "Any changes to the rooms will be discarded."
}

/* Model managing */

var model = saveData;

const toAdd = "to_add";

function moveToRoom (order, from, to){
    if (!model) { console.error("Model is null", order, from, to); return false; }
    if (!model[from]) { console.error("Parent is null", order, from, to); return false; }
    if (!model[to]) { console.error("Destination is null", order, from, to); return false; }
    if (!model[from][toAdd] || !model[from][toAdd].includes(order)) { console.error("Order is not in parent", order, from, to); return false; }
    if (!model[to][toAdd]) model[to][toAdd] = [];
    // Delete order from the original room
    model[from][toAdd] = model[from][toAdd].filter (itm=> itm !== order)
    // Add it to the destination room
    model[to][toAdd].push (order);
    return true;
}

function onSave (){
    if (model['infinite'] && model['infinite'][toAdd] && model['infinite'][toAdd].length > 0) {
        setTimeout(()=>{
            let roomItem = document.querySelector("#room-infinite");
            roomItem.scrollIntoView();
            roomItem.classList.add('drag-forbidden');
            setTimeout(()=>roomItem.classList.remove('drag-forbidden'), 3000);
        }, 100);
    } else {
        document.getElementById('modalConfirmDialog').setAttribute('open', 'true');
    }
}

initObjects ();