const apiBase = "http://127.0.0.1:5000/api";

// Elements
const habitNameInput = document.getElementById("habitName");
const habitTypeSelect = document.getElementById("habitType");
const importanceSelect = document.getElementById("importance");
const reportHabitSelect = document.getElementById("reportHabit");
const habitResultSelect = document.getElementById("habitResult");

const totalPointsElem = document.getElementById("totalPoints");
const rewardBadgeElem = document.getElementById("rewardBadge");
const currentStreakElem = document.getElementById("currentStreak");
const currentGoalElem = document.getElementById("currentGoal");
const habitListElem = document.getElementById("habitList");

const rewardInfoBtn = document.getElementById("rewardInfoBtn");
const rewardPopup = document.getElementById("rewardPopup");
const rewardText = document.getElementById("rewardText");

// ------------------------
// API Calls
// ------------------------
async function fetchJSON(url, options) {
    try {
        const res = await fetch(url, options);
        if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
        return await res.json();
    } catch (err) {
        console.error("Fetch error:", err);
        alert("Failed to fetch from server.");
        return null;
    }
}

// ------------------------
// Habit Functions
// ------------------------
async function addHabit() {
    const data = {
        username: "default_user",
        habit_name: habitNameInput.value,
        habit_type: habitTypeSelect.value,
        importance: importanceSelect.value
    };
    if (!data.habit_name) return alert("Enter habit name");
    
    const res = await fetchJSON(`${apiBase}/add_habit`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    });
    if (res && res.success) {
        habitNameInput.value = "";
        await loadHabits();
    }
}

async function loadHabits() {
    const res = await fetchJSON(`${apiBase}/get_habits?username=default_user`);
    if (!res) return;
    habitListElem.innerHTML = "";
    reportHabitSelect.innerHTML = "";
    res.habits.forEach(h => {
        const li = document.createElement("li");
        li.textContent = `${h.name} (${h.type}, ${h.importance})`;
        habitListElem.appendChild(li);

        const option = document.createElement("option");
        option.value = h.id;
        option.textContent = h.name;
        reportHabitSelect.appendChild(option);
    });
}

// ------------------------
// Report Functions
// ------------------------
async function submitReport() {
    const habit_id = reportHabitSelect.value;
    const result = habitResultSelect.value;
    if (!habit_id) return alert("Select a habit");

    const res = await fetchJSON(`${apiBase}/submit_report`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({username:"default_user", habit_id, result})
    });

    if (res && res.success) {
        alert("Report submitted!");
        await loadStats();
        await loadHabits();
    }
}

// ------------------------
// Stats Functions
// ------------------------
async function loadStats() {
    const res = await fetchJSON(`${apiBase}/get_stats?username=default_user`);
    if (!res) return;
    totalPointsElem.textContent = res.total_points || 0;
    currentStreakElem.textContent = res.streak_weeks || 0;
    currentGoalElem.textContent = res.current_goal || 100;
    rewardBadgeElem.textContent = res.last_reward ? res.last_reward.reward_type : "None";
}

// ------------------------
// Weekly Reward Info
// ------------------------
rewardInfoBtn.addEventListener("click", async (e) => {
    e.stopPropagation(); // prevent document click from closing immediately
    const res = await fetchJSON(`${apiBase}/get_weekly_reward_info`);
    if (!res) return;
    rewardText.innerHTML = `
        <strong>Weekly Reward Info:</strong><br>
        Base goal: ${res.base_goal}<br>
        Increase per week: ${res.increase_pct}%<br>
        Checkpoints: ${res.checkpoints.join(", ")}<br>
        Notes: ${res.notes}
    `;
    rewardPopup.style.display = "block";
});

// Hide reward popup on outside click
document.addEventListener("click", () => {
    rewardPopup.style.display = "none";
});

// Prevent popup from hiding when clicking inside
rewardPopup.addEventListener("click", e => e.stopPropagation());

// ------------------------
// Init
// ------------------------
async function init() {
    await loadHabits();
    await loadStats();
}

init();
