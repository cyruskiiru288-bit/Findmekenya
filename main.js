const API_URL = "https://findmekenya-api.onrender.com";


// ===== NAVBAR =====
let loggedIn = JSON.parse(localStorage.getItem("loggedInFundi"));
let navLogin = document.getElementById("navLogin");
let navLogout = document.getElementById("navLogout");

if (loggedIn) {
    if (navLogin) navLogin.style.display = "none";
    if (navLogout) navLogout.style.display = "block";
} else {
    if (navLogin) navLogin.style.display = "block";
    if (navLogout) navLogout.style.display = "none";
}

if (navLogout) {
    navLogout.addEventListener("click", function() {
        localStorage.removeItem("loggedInFundi");
        window.location.href = "index.html";
    });
}

// ===== HOME PAGE =====
let getStartedBtn = document.getElementById("getStartedBtn");
let choiceBtn = document.getElementById("choiceBtn");

if (getStartedBtn) {
    getStartedBtn.addEventListener("click", function() {
        choiceBtn.style.display = "flex";
        getStartedBtn.style.display = "none";
    });
}

// ===== SEARCH PAGE =====
async function searchFundis() {
    let query = document.getElementById("searchInput").value.trim();
    let resultsDiv = document.getElementById("results");

    if (!resultsDiv) return;

    resultsDiv.innerHTML = "<p>Searching...</p>";

    try {
        let url = `${API_URL}/fundis`;
        if (query) {
            url += `?skill=${encodeURIComponent(query)}`;
        }

        let response = await fetch(url);
        let data = await response.json();

        if (data.error) {
            resultsDiv.innerHTML = `<p>${data.error}</p>`;
            return;
        }

        displayResults(data.fundis);

    } catch (error) {
        resultsDiv.innerHTML = "<p>Could not connect to server. Please try again!</p>";
    }
}

function displayResults(results) {
    let resultsDiv = document.getElementById("results");

    if (!resultsDiv) return;

    if (results.length === 0) {
        resultsDiv.innerHTML = "<p>No fundis found. Try a different search!</p>";
        return;
    }

    let html = "";
    results.forEach(function(fundi) {
        html += `
            <div class="fundi-card">
                ${fundi.photo_url ? `<img src="${fundi.photo_url}" alt="${fundi.name}" style="width:100px; height:100px; border-radius:50%; object-fit:cover;"/>` : ""}
                <h3>${fundi.name} ${fundi.is_verified ? "✅ Verified" : ""}</h3>
                <p>🔧 ${fundi.skill}</p>
                <p>📍 ${fundi.location}</p>
                <p>${fundi.bio}</p>
                <div class="contact-buttons">
                    <a href="tel:${fundi.phone}"><button class="btn">📞 Call</button></a>
                    <a href="https://wa.me/${fundi.whatsapp}"><button class="btn">💬 WhatsApp</button></a>
                    <a href="https://facebook.com/${fundi.facebook}"><button class="btn">👤 Facebook</button></a>
                </div>
            </div>
        `;
    });

    resultsDiv.innerHTML = html;
}

let searchBtn = document.getElementById("searchBtn");
if (searchBtn) {
    searchBtn.addEventListener("click", function() {
        searchFundis();
    });
}

let chips = document.querySelectorAll(".chip");
if (chips) {
    chips.forEach(function(chip) {
        chip.addEventListener("click", function() {
            let text = chip.textContent.replace(/[^\w\s]/g, "").trim();
            document.getElementById("searchInput").value = text;
            searchFundis();
        });
    });
}

// ===== REGISTER PAGE =====
async function checkSpots() {
    let spotsLeft = document.getElementById("spotsLeft");
    if (!spotsLeft) return;

    try {
        let response = await fetch(`${API_URL}/spots-remaining`);
        let data = await response.json();

        if (data.free_available) {
            spotsLeft.textContent = `🎉 ${data.spots_remaining} FREE spots remaining! Pay Ksh 32 first month and get 6 months FREE!`;
            spotsLeft.style.color = "green";
        } else {
            spotsLeft.textContent = "All free spots taken! Choose a plan below.";
            spotsLeft.style.color = "red";
        }
    } catch (error) {
        console.log("Could not check spots");
    }
}

checkSpots();

let registerBtn = document.getElementById("registerBtn");
if (registerBtn) {
    registerBtn.addEventListener("click", async function() {
        let name = document.getElementById("regName").value.trim();
        let phone = document.getElementById("regPhone").value.trim();
        let email = document.getElementById("regEmail").value.trim();
        let password = document.getElementById("regPassword").value.trim();
        let errorMsg = document.getElementById("registerError");

        if (name === "") {
            errorMsg.textContent = "Please enter your full name!";
            errorMsg.style.display = "block";
            return;
        }
        if (phone === "") {
            errorMsg.textContent = "Please enter your phone number!";
            errorMsg.style.display = "block";
            return;
        }
        if (email === "") {
            errorMsg.textContent = "Please enter your email!";
            errorMsg.style.display = "block";
            return;
        }
        if (password.length < 6) {
            errorMsg.textContent = "Password must be at least 6 characters!";
            errorMsg.style.display = "block";
            return;
        }

        try {
            let response = await fetch(`${API_URL}/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, email, password, phone })
            });

            let data = await response.json();

            if (data.error) {
                errorMsg.textContent = data.error;
                errorMsg.style.display = "block";
                return;
            }

            localStorage.setItem("loggedInFundi", JSON.stringify({
                name, email, phone, user_id: data.user_id
            }));
            errorMsg.style.display = "none";

            // Always show payment plans
            document.getElementById("subscriptionPlans").style.display = "block";

            // Update spots message
            let spotsResponse = await fetch(`${API_URL}/spots-remaining`);
            let spotsData = await spotsResponse.json();

            if (spotsData.free_available) {
                document.getElementById("spotsLeft").textContent = "🎉 You qualify for 6 months FREE after paying your first month of Ksh 32!";
                document.getElementById("spotsLeft").style.color = "green";
            }

        } catch (error) {
            errorMsg.textContent = "Could not connect to server. Please try again!";
            errorMsg.style.display = "block";
        }
    });
}

// ===== PLAN SELECTION WITH PAYSTACK =====
const planAmounts = {
    "monthly": 32,
    "3months": 80,
    "6months": 180
};

let planBtns = document.querySelectorAll(".plan-btn");
if (planBtns) {
    planBtns.forEach(function(btn) {
        btn.addEventListener("click", async function() {
            let plan = btn.getAttribute("data-plan");
            let amount = planAmounts[plan];
            let fundi = JSON.parse(localStorage.getItem("loggedInFundi"));

            try {
                btn.textContent = "Processing...";
                btn.disabled = true;

                let response = await fetch(`${API_URL}/payment/initialize`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        phone: fundi.phone,
                        email: fundi.email,
                        amount: amount,
                        user_id: fundi.user_id,
                        plan: plan
                    })
                });

                let data = await response.json();

                if (data.error) {
                    alert("Payment failed: " + data.error);
                    btn.textContent = "Choose";
                    btn.disabled = false;
                    return;
                }

                // Save reference for verification later
                localStorage.setItem("paymentReference", data.reference);
                localStorage.setItem("selectedPlan", plan);

                // Redirect to Paystack payment page
                window.location.href = data.payment_url;

            } catch (error) {
                alert("Could not connect to server. Please try again!");
                btn.textContent = "Choose";
                btn.disabled = false;
            }
        });
    });
}

// ===== LOGIN PAGE =====
let loginBtn = document.getElementById("loginBtn");
if (loginBtn) {
    loginBtn.addEventListener("click", async function() {
        let email = document.getElementById("loginEmail").value.trim();
        let password = document.getElementById("loginPassword").value.trim();
        let errorMsg = document.getElementById("loginError");

        if (email === "") {
            errorMsg.textContent = "Please enter your email!";
            errorMsg.style.display = "block";
            return;
        }
        if (password === "") {
            errorMsg.textContent = "Please enter your password!";
            errorMsg.style.display = "block";
            return;
        }

        try {
            let response = await fetch(`${API_URL}/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            });

            let data = await response.json();

            if (data.error) {
                errorMsg.textContent = data.error;
                errorMsg.style.display = "block";
                return;
            }

            localStorage.setItem("loggedInFundi", JSON.stringify({
                name: data.name,
                email: data.email,
                user_id: data.user_id
            }));
            errorMsg.style.display = "none";
            window.location.href = "fundidashboard.html";

        } catch (error) {
            errorMsg.textContent = "Could not connect to server. Please try again!";
            errorMsg.style.display = "block";
        }
    });
}

// ===== FUNDI DASHBOARD =====
let loggedInFundi = JSON.parse(localStorage.getItem("loggedInFundi"));

if (document.getElementById("profileSection")) {
    if (!loggedInFundi) {
        window.location.href = "login.html";
    }

    document.getElementById("fundiName").textContent = loggedInFundi.name;

    async function loadProfile() {
        try {
            let response = await fetch(`${API_URL}/profile/${loggedInFundi.user_id}`);
            let data = await response.json();

            if (!data.error) {
                document.getElementById("profileName").value = loggedInFundi.name || "";
                document.getElementById("profileSkill").value = data.skill || "";
                document.getElementById("profileLocation").value = data.location || "";
                document.getElementById("profilePhone").value = loggedInFundi.phone || "";
                document.getElementById("profileWhatsapp").value = data.whatsapp || "";
                document.getElementById("profileFacebook").value = data.facebook || "";
                document.getElementById("profileBio").value = data.bio || "";
            }
        } catch (error) {
            console.log("No profile yet");
        }
    }

    loadProfile();

    let saveProfileBtn = document.getElementById("saveProfileBtn");
    if (saveProfileBtn) {
        saveProfileBtn.addEventListener("click", async function() {
            let skill = document.getElementById("profileSkill").value.trim();
            let location = document.getElementById("profileLocation").value.trim();
            let whatsapp = document.getElementById("profileWhatsapp").value.trim();
            let facebook = document.getElementById("profileFacebook").value.trim();
            let bio = document.getElementById("profileBio").value.trim();
            let photo = document.getElementById("profilePhoto").files[0];
            let errorMsg = document.getElementById("profileError");
            let successMsg = document.getElementById("profileSuccess");

            if (skill === "") {
                errorMsg.textContent = "Please enter your skill!";
                errorMsg.style.display = "block";
                successMsg.style.display = "none";
                return;
            }
            if (location === "") {
                errorMsg.textContent = "Please enter your location!";
                errorMsg.style.display = "block";
                successMsg.style.display = "none";
                return;
            }
            if (bio === "") {
                errorMsg.textContent = "Please write a short bio!";
                errorMsg.style.display = "block";
                successMsg.style.display = "none";
                return;
            }

            try {
                let response = await fetch(`${API_URL}/profile`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        user_id: loggedInFundi.user_id,
                        skill, location, bio, whatsapp, facebook
                    })
                });

                let data = await response.json();

                if (data.error) {
                    errorMsg.textContent = data.error;
                    errorMsg.style.display = "block";
                    successMsg.style.display = "none";
                    return;
                }

                if (photo) {
                    let formData = new FormData();
                    formData.append("file", photo);

                    let photoResponse = await fetch(`${API_URL}/upload-photo/${loggedInFundi.user_id}`, {
                        method: "POST",
                        body: formData
                    });

                    let photoData = await photoResponse.json();
                    if (photoData.error) {
                        errorMsg.textContent = "Profile saved but photo failed!";
                        errorMsg.style.display = "block";
                        return;
                    }
                }

                errorMsg.style.display = "none";
                successMsg.textContent = "Profile saved! Clients can now find you! ✅";
                successMsg.style.display = "block";

            } catch (error) {
                errorMsg.textContent = "Could not connect to server!";
                errorMsg.style.display = "block";
            }
        });
    }

    let logoutBtn = document.getElementById("logoutBtn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", function() {
            localStorage.removeItem("loggedInFundi");
            window.location.href = "index.html";
        });
    }
}

// ===== PAYMENT SUCCESS PAGE =====
if (document.getElementById("loadingMsg")) {
    async function verifyPayment() {
        let reference = localStorage.getItem("paymentReference");
        let plan = localStorage.getItem("selectedPlan");
        let fundi = JSON.parse(localStorage.getItem("loggedInFundi"));

        if (!reference || !fundi) {
            document.getElementById("loadingMsg").style.display = "none";
            document.getElementById("errorMsg").style.display = "block";
            return;
        }

        try {
            let response = await fetch(`${API_URL}/payment/verify`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    reference: reference,
                    user_id: fundi.user_id,
                    plan: plan
                })
            });

            let data = await response.json();

            document.getElementById("loadingMsg").style.display = "none";

            if (data.error) {
                document.getElementById("errorMsg").style.display = "block";
            } else {
                // Check if free 500 user
                let spotsCheck = await fetch(`${API_URL}/spots-remaining`);
                let spotsData = await spotsCheck.json();

                if (spotsData.free_available) {
                    await fetch(`${API_URL}/free-subscription`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ user_id: fundi.user_id })
                    });
                }

                localStorage.removeItem("paymentReference");
                document.getElementById("successMsg").style.display = "block";
            }

        } catch (error) {
            document.getElementById("loadingMsg").style.display = "none";
            document.getElementById("errorMsg").style.display = "block";
        }
    }

    verifyPayment();
}