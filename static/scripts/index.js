document.addEventListener("DOMContentLoaded", () => {
  const wsClient = new WebSocket("ws://localhost:8000/ws/client");
  let connectionStatus = "Disconnected";
  const statusIndicator = document.createElement("div");
  const canvas = document.getElementById("robotMap");
  const ctx = canvas.getContext("2d");
  const scale = 0.1;

  let points = [];
  let walls = [];
  function initializeStatusIndicator() {
    const batteryContainer = document.querySelector(".battery-status");
    statusIndicator.classList.add("status-indicator", "disconnected");
    statusIndicator.textContent = connectionStatus;
    batteryContainer.parentNode.insertBefore(statusIndicator, batteryContainer);
  }

  function sendMessage(message) {
    console.log("Sending: " + message);
    wsClient.send(message);
  }

  function updateConnectionStatus(isConnected) {
    if (isConnected) {
      connectionStatus = "Connected";
      statusIndicator.classList.remove("disconnected");
      statusIndicator.classList.add("connected");
      statusIndicator.textContent = connectionStatus;
    } else {
      connectionStatus = "Disconnected";
      statusIndicator.classList.remove("connected");
      statusIndicator.classList.add("disconnected");
      statusIndicator.textContent = connectionStatus;
    }
  }

  initializeStatusIndicator();

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Рисуем точки робота
    ctx.fillStyle = "blue";
    points.forEach((p) => {
      ctx.beginPath();
      ctx.arc(p.x * scale, p.y * scale, 3, 0, Math.PI * 2);
      ctx.fill();
    });

    // Рисуем линии между стенами
    ctx.strokeStyle = "red";
    ctx.lineWidth = 2;
    ctx.beginPath();
    walls.forEach((w, i) => {
      if (i > 0) {
        ctx.moveTo(walls[i - 1].x * scale, walls[i - 1].y * scale);
        ctx.lineTo(w.x * scale, w.y * scale);
      }
    });
    ctx.stroke();
  }

  function updateMap(data) {
    points = [];
    walls = [];

    data.forEach(({ df, ds, ang, dh }, index) => {
      const prev = points[index - 1] || { x: 0, y: 0, angle: 0 };

      let x = prev.x + dh * Math.sin((prev.angle * Math.PI) / 180);
      let y = prev.y + dh * Math.cos((prev.angle * Math.PI) / 180);
      let angle = prev.angle + ang;

      points.push({ x, y, angle });

      walls.push({ x: x, y: y + df });
      walls.push({ x: x + ds, y: y });
    });
    draw();
  }

  function handleSocketData(data) {
    const noDataPattern = /data:log:vol:-,cur:-,df:-,ds:-,ang:-,dh:-,bat:-/;

    if (noDataPattern.test(data)) {
      updateConnectionStatus(false);
    } else {
      updateConnectionStatus(true);
      const logData = event.data.slice(9).split(",");
      const dataMap = {};
      logData.forEach((item) => {
        const [key, value] = item.split(":");
        dataMap[key] = value;
      });

      document.getElementById("voltage").textContent = dataMap["vol"] + " V";
      document.getElementById("current").textContent = dataMap["cur"] + " mA";
      document.getElementById("angle").textContent = dataMap["ang"] + "°";
      document.getElementById("front").textContent = dataMap["df"] + " mm";
      document.getElementById("side").textContent = dataMap["ds"] + " mm";
      document.getElementById("hall").textContent = dataMap["dh"] + " mm";

      updateMap([
        {
          df: dataMap["df"],
          ds: dataMap["ds"],
          ang: dataMap["ang"],
          dh: dataMap["dh"],
        },
      ]);

      const batteryLevel = parseInt(dataMap["bat"], 10);
      const batteryIcon = document.getElementById("battery-icon");
      const batteryPercentage = document.getElementById("battery-percentage");
      batteryIcon.style.width = `${batteryLevel}%`;
      batteryPercentage.textContent = `${batteryLevel}%`;

      batteryIcon.classList.remove(
        "battery-full",
        "battery-medium",
        "battery-low",
      );
      if (batteryLevel >= 67) {
        batteryIcon.classList.add("battery-full");
      } else if (batteryLevel >= 34) {
        batteryIcon.classList.add("battery-medium");
      } else {
        batteryIcon.classList.add("battery-low");
      }
    }
  }

  wsClient.onmessage = function (event) {
    const data = event.data;
    const imageWrapper = document.querySelector(".image-wrapper");
    const imageElement = document.getElementById("image");

    if (data.startsWith("data:image")) {
      imageElement.src = data;
      imageWrapper.style.display = "block";
    } else if (data.startsWith("data:log")) {
      handleSocketData(data);
    }
  };

  const style = document.createElement("style");
  style.innerHTML = `
        .status-indicator {
            padding: 5px 10px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            color: #ffffff;
            margin-right: 10px;
        }
        .connected {
            background-color: #4CAF50;
        }
        .disconnected {
            background-color: #F44336;
        }
    `;
  let keysPressed = {};

  document.addEventListener("keydown", function (event) {
    if (!keysPressed[event.key]) {
      keysPressed[event.key] = true;
      switch (event.key) {
        case "ArrowUp":
          sendMessage("remote_forward");
          break;
        case "ArrowDown":
          sendMessage("remote_backward");
          break;
        case "ArrowLeft":
          sendMessage("remote_left");
          break;
        case "ArrowRight":
          sendMessage("remote_right");
          break;
      }
    }
  });

  document.addEventListener("keyup", function (event) {
    if (keysPressed[event.key]) {
      keysPressed[event.key] = false;
      sendMessage("remote_stop");
    }
  });

  document.querySelectorAll("button[data-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const action = button.getAttribute("data-action");
      sendMessage(action);
    });
  });
});
