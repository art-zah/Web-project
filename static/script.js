function goToAdmin() {
    window.location.href = "/admin";
}

async function checkAdmin() {
    try {
        const response = await fetch("/api/is-admin");
        const data = await response.json();

        const adminBtn = document.getElementById("admin-btn");

        if (data.is_admin) {
            adminBtn.style.display = "inline-block";
        } else {
            adminBtn.style.display = "none";
        }

    } catch (error) {
        console.error("Ошибка проверки админа:", error);
    }
}

function showRegisterForm() {
    document.getElementById("login-form").style.display = "none";
    document.getElementById("register-form").style.display = "block";
}

function showLoginForm() {
    document.getElementById("register-form").style.display = "none";
    document.getElementById("login-form").style.display = "block";
}

async function register() {
    const email = document.getElementById("register-email").value;
    const password = document.getElementById("register-password").value;

    const response = await fetch("/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
    });

    const result = await response.json();
    alert(result.message || result.error);

    if (response.ok) {
        showLoginForm();
    }
}

async function login() {
    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;

    const response = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
    });

    const result = await response.json();
    alert(result.message || result.error);

    if (response.ok) {
        document.getElementById("login-form").style.display = "none";
        document.getElementById("user-info").style.display = "block";
        document.getElementById("clubs-container").style.display = "block";
        document.getElementById("user-email").textContent = email;

        checkAdmin();
    }
}

async function logout() {
    await fetch("/logout", { method: "POST" });
    document.getElementById("user-info").style.display = "none";
    document.getElementById("clubs-container").style.display = "none"
    document.getElementById("login-form").style.display = "block";

    checkAdmin();
}

async function checkAuth() {
    const response = await fetch("/is-logged-in");
    const result = await response.json();

    if (result.is_logged_in) {
        document.getElementById("user-info").style.display = "block";
        document.getElementById("clubs-container").style.display = "block"
        document.getElementById("user-email").textContent = result.us;
        document.getElementById("login-form").style.display = "none";
    } else {
        document.getElementById("user-info").style.display = "none";
        document.getElementById("clubs-container").style.display = "none"
        document.getElementById("login-form").style.display = "block";
    }
}

// Запускаем проверку при загрузке страницы
window.onload = () => {
    checkAuth();
    loadClubs();
    checkAdmin();
};


// Загрузка клубов при открытии страницы
async function loadClubs() {
    const response = await fetch("/api/clubs");
    const clubs = await response.json();

    const container = document.getElementById("clubs-container");
    container.innerHTML = "";

    clubs.forEach(club => {
        const clubDiv = document.createElement("div");
        clubDiv.className = "club";
        clubDiv.innerHTML = `
            <h2>${club.name}</h2>
            <p class="p">${club.address}</p>
            <div id="computers-${club.id}"></div>
        `;

        container.appendChild(clubDiv);

        // Загрузка компьютеров для клуба
        loadComputers(club.id);
    });
}

// Загрузка компьютеров клуба
async function loadComputers(clubId) {
    const response = await fetch(`/api/clubs/${clubId}/computers`);
    const computers = await response.json();

    const compContainer = document.getElementById(`computers-${clubId}`);
    compContainer.innerHTML = "";

    computers.forEach(comp => {
        const compDiv = document.createElement("div");
        compDiv.className = `computer-row ${comp.status === "busy" ? "busy" : ""}`;

        compDiv.innerHTML = `
            <div class="computer-left">
                <strong>${comp.model}</strong>
                <span class="status">
                    ${comp.status === "free" ? "Свободен" : "Занят"}
                </span>
            </div>
            <div class="computer-right"></div>
        `;

        if (comp.status === "free") {
            const bookBtn = document.createElement("button");
            bookBtn.textContent = "Забронировать";
            bookBtn.className = "bookBtn";
            bookBtn.onclick = () => bookComputer(clubId, comp.id);

            compDiv.querySelector(".computer-right").appendChild(bookBtn);
        }

        compContainer.appendChild(compDiv);
    });
}

// Бронирование компьютера
async function bookComputer(clubId, computerId) {

    const response = await fetch("/api/bookings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            club_id: clubId,
            computer_id: computerId,
            hours: 1
        })
    });

    if (response.ok) {
        alert("Бронь создана!");
        loadComputers(clubId); // Обновляем список компьютеров
    } else {
        alert("Ошибка бронирования (возможно этот компьютер забронировали только что)");
        loadComputers(clubId)
    }
}

// Запуск при загрузке страницы
window.onload = () => {
    checkAuth();
    loadClubs();
    checkAdmin();
};