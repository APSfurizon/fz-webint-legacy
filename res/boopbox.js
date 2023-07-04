const box = document.getElementById("msgbox");
const msgbox = document.getElementById("msgcontent");
const wolf = document.getElementById("wolf");
const tiger = document.getElementById("tiger");
const touch = document.getElementById("touch");
const bye_elements = document.getElementsByClassName('bye');
const welcome_back_elements = document.getElementsByClassName('welcome-back');

const apiUrl = "/manage/api/events.json";
let currentTime = new Date();

const searchParams = new URL(window.location.href).searchParams;
const boopboxId = searchParams.get('id');

if(!boopboxId) {
	alert("Boopbox id is not set!");
}

window.onload = function() {
	updateEvents();
	loop();
	clock();
	//fastForward();
}

let cachedData = null;

function updateEvents() {
	fetch(apiUrl)
		.then(response => response.json())
		.then(data => {
			cachedData = data;
			updateDivs(data);
		})
		.catch(error => {
			if (cachedData) {
				updateDivs(cachedData);
			} else {
				console.error('Request failed and no cached data available:', error);
			}
		});
}

function updateDivs(data) {
	const eventsContainer = document.getElementById("eventsbox");
	const tenMinutesFromNow = new Date(currentTime.getTime() + 10 * 60000);
	const tenMinutesAgo = new Date(currentTime.getTime() - 10 * 60000);
	let visibleEvents = 0;

	data.forEach(event => {
		const eventStart = new Date(event.start);
		const eventEnd = new Date(event.end);
		
		const eventPercent = Math.max(0, Math.min(100, ((currentTime - eventStart) / (eventEnd - eventStart)) * 100));

		if (eventStart <= tenMinutesFromNow && eventEnd >= tenMinutesAgo) {
			
			visibleEvents++;
			let eventDiv = document.getElementById(`event-${event.id}`);

			if (!eventDiv) {
				eventDiv = document.createElement('div');
				eventDiv.id = `event-${event.id}`;
				eventsContainer.appendChild(eventDiv);
			}

			eventDiv.innerHTML = `
				<span data-location="${event.location}">${event.location}</span>
				<h2>${event.title}</h2>
				<p>${event.about}</p>
				<p style="text-align:right;">${Math.ceil(Math.max(0, (eventEnd - currentTime) / 60000))} minutes left</p>
			`;
			
			eventDiv.style.borderImage = `linear-gradient(to right, darkblue, darkorchid ${eventPercent}%, rgba(0,0,0,0) ${eventPercent+0.1}%) 1`;
			
		} else {
			const eventDiv = document.getElementById(`event-${event.id}`);

			if (eventDiv) {
				eventDiv.remove();
			}
		}
	});

	if(visibleEvents == 0) {
		document.getElementById("nothing-happening").style.display = 'block';
	} else {
		document.getElementById("nothing-happening").style.display = 'none';
	}
}

function clock() {
	setInterval(() => {
		currentTime = new Date();
		let ts = currentTime.toString();
		ts = ts.replace("GMT+0200 (Central European Summer Time)", "");
		ts = ts.replace("2023", "<br />");
		document.getElementById("clock").innerHTML = ts;
	}, 1000);
}

function fastForward() {
	currentTime = new Date("2023-05-29T18:00Z");
	setInterval(() => {
	    updateDivs(cachedData);
	    currentTime.setMinutes(currentTime.getMinutes()+1);
  	}, 100);
}

async function loop() {
	while (true) {
		try {
			document.getElementById("nfcstat").removeAttribute('disabled');
			const response = await fetch("/boop/getqueue/"+boopboxId);
			const json = await response.json();
			document.getElementById("nfcstat").setAttribute('disabled', 'true');
			for(i = 0; i < json.length; i++) {
				console.log(json[i]);
				document.getElementById('debug').innerHTML = JSON.stringify(json[i]);
				try {
					await window[json[i]["_"]](json[i]);
				} catch (e) {
					document.getElementById('debug').innerHTML = e;
				}
			}
		} catch (e) {
			await new Promise(r => setTimeout(r, 2000));
			console.error(e);
		}
	}
}

/*window.oncontextmenu = function(event) {
	event.preventDefault();
	event.stopPropagation();
	return false;
};*/

async function talk(dict) {

	for (const c of welcome_back_elements) {
		c.classList.add('hidden');
	}

	character = document.getElementById(dict.who);
	character.removeAttribute('disabled');
	box.removeAttribute('disabled');
	for(j = 0;j < dict.msg.length; j++) {
		to = 20;
		msgbox.innerHTML += dict.msg[j];
				
		if(dict.msg[j] == '.') {to = 400;}
		if(dict.msg[j] == ',') {to = 200;}
				
		await new Promise(r => setTimeout(r, to));
	}
	await new Promise(r => setTimeout(r, 1000));
}

async function bye(dict) {

	msgbox.innerHTML = '';

	for (const c of bye_elements) {
		c.setAttribute('disabled', 'true');
	}
	
	for (const c of welcome_back_elements) {
		c.classList.remove('hidden');
	}
}

async function play(dict) {
	const audio = new Audio(dict.src);
	await audio.play();
}

async function wait(dict) {
	return new Promise((resolve) => {
		setTimeout(resolve, dict.time * 1000);
	});
}

async function orchestrate(thing) {
	for(var i = 0; i < msg.length; i++) {
		task = msg[i]
							
		// It's a command
		if(task.length == 3) {
			switch(task) {
				case '!w-':
					wolf.setAttribute('disabled', 'true');
					break;
				case '!t-':
					tiger.setAttribute('disabled', 'true');
					break;
				case '!w+':
					wolf.removeAttribute('disabled');
					break;
				case '!t+':
					tiger.removeAttribute('disabled');
					break;
				case '!s+':
					msgbox.classList.add('yell');
					break;
				case '!s-':
					msgbox.classList.remove('yell');
					break;
				default:
					alert('Invalid command received.' + task);
			}
		
			continue;
		}
		

		touch.setAttribute("disabled", "true");
		
		// It's a text message
		if (task.startsWith('!w:') || task.startsWith('!t:')) {
		
			if(task[1] == 'w' && wolf.getAttribute('disabled') == 'true') {
				wolf.removeAttribute('disabled');
			}
			
			if(task[1] == 't' && tiger.getAttribute('disabled') == 'true') {
				tiger.removeAttribute('disabled');
			}
			
			msgbox.style.color = (task[1] == 'w')?'#FAEBD7':'#ADD8E6';
			
			txt = task.substr(3);



			await new Promise(r => setTimeout(r, 500));
			//touch.removeAttribute("disabled");
			await new Promise(r => setTimeout(r, 1000));
			msgbox.innerHTML = '';

			console.log(task);
		}			
	}	
	
	box.setAttribute('disabled', 'true');			
}
