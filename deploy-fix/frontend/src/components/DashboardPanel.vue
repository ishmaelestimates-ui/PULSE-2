<template>
  <div class="dashboard-panel">
    <div class="sub-tabs">
      <button v-for="t in subTabs" :key="t" class="sub-tab" :class="{ 'sub-tab--active': subTab === t }" @click="subTab = t">
        {{ t }}
      </button>
    </div>

    <p v-if="error" class="hint hint--error">{{ error }}</p>

    <!-- OVERVIEW -->
    <div v-if="subTab === 'Overview'" class="pane">
      <button class="btn-link" @click="loadDashboard">Refresh</button>

      <div v-if="dashboard" class="overview">
        <div class="score-row">
          <div class="score-block">
            <span class="score-value">{{ dashboard.overall_progress }}%</span>
            <span class="score-label">Overall progress</span>
          </div>
          <div class="score-block">
            <span class="score-value" :class="healthClass">{{ dashboard.health_score }}</span>
            <span class="score-label">Health score</span>
          </div>
        </div>

        <div class="progress-bars">
          <div v-for="(pct, stage) in dashboard.progress" :key="stage" class="progress-row">
            <span class="stage-label">{{ stage }}</span>
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: pct + '%' }"></div>
            </div>
            <span class="mono pct-label">{{ pct }}%</span>
          </div>
        </div>

        <h4>Critical path</h4>
        <ol class="critical-path">
          <li v-for="(step, i) in dashboard.critical_path" :key="i">{{ step }}</li>
        </ol>
        <p v-if="!dashboard.critical_path.length" class="hint">Nothing outstanding — fully built out.</p>

        <h4>Upcoming (30 days)</h4>
        <div v-for="(d, i) in dashboard.upcoming_deadlines" :key="i" class="deadline-row">
          <span class="mono">{{ d.date }}</span>
          <span>{{ d.title }}</span>
          <span v-if="d.type === 'festival_deadline' && !d.verified" class="unverified">unverified</span>
        </div>

        <p class="hint">{{ dashboard.team_status_note }}</p>
        <p class="hint">{{ dashboard.note }}</p>
      </div>
    </div>

    <!-- RISKS -->
    <div v-else-if="subTab === 'Risks'" class="pane">
      <button class="btn btn--primary" :disabled="loadingRisks" @click="loadRisks">
        {{ loadingRisks ? "Scanning…" : "Run risk scan" }}
      </button>
      <p v-if="risksNote" class="hint">{{ risksNote }}</p>
      <div v-for="(r, i) in risks" :key="i" class="risk-card" :class="`risk-card--${r.severity}`">
        <div class="risk-top">
          <span class="risk-category">{{ r.category }}</span>
          <span class="risk-severity">{{ r.severity }}</span>
        </div>
        <p class="body-text">{{ r.description }}</p>
        <p class="hint">→ {{ r.recommended_action }}</p>
      </div>
      <p v-if="risksChecked && risks.length === 0" class="hint">No risks detected.</p>
    </div>

    <!-- FINANCES -->
    <div v-else-if="subTab === 'Finances'" class="pane">
      <form class="add-form" @submit.prevent="addBudget">
        <input v-model="budgetForm.category" placeholder="Category" required />
        <input v-model.number="budgetForm.amount" type="number" placeholder="Budget" required />
        <input v-model.number="budgetForm.spent" type="number" placeholder="Spent" />
        <button class="btn btn--ghost" type="submit">+ Add</button>
      </form>

      <div v-if="finances" class="finance-summary">
        <span>Budget: ${{ finances.total_budget.toLocaleString() }}</span>
        <span>Spent: ${{ finances.total_spent.toLocaleString() }}</span>
        <span :class="{ 'over-budget': finances.remaining < 0 }">Remaining: ${{ finances.remaining.toLocaleString() }}</span>
      </div>
      <div v-for="item in finances?.items || []" :key="item.id" class="budget-row">
        <span>{{ item.category }}</span>
        <span class="mono">${{ item.spent.toLocaleString() }} / ${{ item.amount.toLocaleString() }}</span>
      </div>
      <p v-for="(s, i) in finances?.reallocation_suggestions || []" :key="i" class="hint hint--warn">{{ s }}</p>
    </div>

    <!-- TIMELINE -->
    <div v-else-if="subTab === 'Timeline'" class="pane">
      <form class="add-form" @submit.prevent="addMilestoneItem">
        <input v-model="milestoneForm.title" placeholder="Milestone" required />
        <input v-model="milestoneForm.due_date" type="date" />
        <button class="btn btn--ghost" type="submit">+ Add</button>
      </form>
      <div v-for="m in milestones" :key="m.id" class="milestone-row" :class="{ 'milestone-row--overdue': m.overdue }">
        <span>{{ m.title }}</span>
        <span class="mono">{{ m.due_date || "no date" }}</span>
        <span class="status-badge">{{ m.overdue ? "overdue" : m.status }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import api from "../api/client";

const props = defineProps({
  episodeId: { type: Number, required: true },
});

const subTabs = ["Overview", "Risks", "Finances", "Timeline"];
const subTab = ref("Overview");
const error = ref("");

const dashboard = ref(null);
const healthClass = computed(() => {
  const s = dashboard.value?.health_score ?? 0;
  return s >= 70 ? "score-good" : s >= 40 ? "score-mid" : "score-bad";
});

const risks = ref([]);
const risksNote = ref("");
const risksChecked = ref(false);
const loadingRisks = ref(false);

const finances = ref(null);
const budgetForm = reactive({ category: "", amount: null, spent: 0 });

const milestones = ref([]);
const milestoneForm = reactive({ title: "", due_date: "" });

async function loadDashboard() {
  error.value = "";
  try {
    dashboard.value = await api.getDashboard(props.episodeId);
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to load dashboard.";
  }
}

async function loadRisks() {
  loadingRisks.value = true;
  error.value = "";
  try {
    const data = await api.getRisks(props.episodeId);
    risks.value = data.risks;
    risksNote.value = data.note;
    risksChecked.value = true;
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to run risk scan.";
  } finally {
    loadingRisks.value = false;
  }
}

async function loadFinances() {
  try {
    finances.value = await api.getFinances(props.episodeId);
  } catch (err) {
    // non-fatal
  }
}

async function addBudget() {
  if (!budgetForm.category || budgetForm.amount == null) return;
  try {
    await api.addBudgetItem(props.episodeId, { ...budgetForm });
    await loadFinances();
    budgetForm.category = "";
    budgetForm.amount = null;
    budgetForm.spent = 0;
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to add budget item.";
  }
}

async function loadMilestones() {
  try {
    const data = await api.getTimeline(props.episodeId);
    milestones.value = data.milestones;
  } catch (err) {
    // non-fatal
  }
}

async function addMilestoneItem() {
  if (!milestoneForm.title) return;
  try {
    const payload = { title: milestoneForm.title };
    if (milestoneForm.due_date) payload.due_date = milestoneForm.due_date;
    await api.addMilestone(props.episodeId, payload);
    await loadMilestones();
    milestoneForm.title = "";
    milestoneForm.due_date = "";
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to add milestone.";
  }
}

onMounted(() => {
  loadDashboard();
  loadFinances();
  loadMilestones();
});
</script>

<style scoped>
.dashboard-panel {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.sub-tabs {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.sub-tab {
  background: var(--surface-inset);
  border: 1px solid var(--border);
  color: var(--text-faint);
  font-size: 11.5px;
  padding: 6px 11px;
  border-radius: 999px;
}
.sub-tab--active {
  background: var(--primary-dim);
  border-color: var(--primary);
  color: white;
}
.pane {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.hint {
  font-size: 11.5px;
  color: var(--text-faint);
}
.hint--error {
  color: var(--weak);
}
.hint--warn {
  color: var(--bookend);
}
.body-text {
  font-size: 12.5px;
  color: var(--text-dim);
  line-height: 1.5;
}

.score-row {
  display: flex;
  gap: 12px;
}
.score-block {
  flex: 1;
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 14px;
  text-align: center;
}
.score-value {
  display: block;
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
}
.score-good { color: var(--secondary); }
.score-mid { color: var(--bookend); }
.score-bad { color: var(--weak); }
.score-label {
  font-size: 10.5px;
  color: var(--text-faint);
}

.progress-bars {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.progress-row {
  display: grid;
  grid-template-columns: 90px 1fr 40px;
  align-items: center;
  gap: 8px;
}
.stage-label {
  font-size: 11px;
  text-transform: capitalize;
  color: var(--text-dim);
}
.progress-track {
  height: 6px;
  border-radius: 999px;
  background: var(--surface-inset);
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--primary);
}
.pct-label {
  font-size: 10.5px;
  color: var(--text-faint);
  text-align: right;
}

.dashboard-panel h4 {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-faint);
  margin-top: 6px;
}
.critical-path {
  padding-left: 18px;
  font-size: 12.5px;
  color: var(--text-dim);
}
.critical-path li {
  padding: 2px 0;
}

.deadline-row {
  display: flex;
  gap: 10px;
  align-items: center;
  font-size: 12px;
  color: var(--text-dim);
  padding: 4px 0;
}
.unverified {
  color: var(--bookend);
  font-size: 10px;
}

.risk-card {
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-left: 3px solid var(--border-bright);
  border-radius: var(--radius-md);
  padding: 10px 12px;
}
.risk-card--high { border-left-color: var(--weak); }
.risk-card--medium { border-left-color: var(--bookend); }
.risk-card--low { border-left-color: var(--text-faint); }
.risk-top {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  text-transform: uppercase;
  color: var(--text-faint);
}

.add-form {
  display: flex;
  gap: 6px;
}
.add-form input {
  flex: 1;
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 7px 9px;
  font-size: 12px;
}

.finance-summary {
  display: flex;
  gap: 16px;
  font-size: 12.5px;
  color: var(--text-dim);
}
.over-budget {
  color: var(--weak);
}
.budget-row, .milestone-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
  font-size: 12.5px;
  color: var(--text-dim);
}
.milestone-row--overdue {
  color: var(--weak);
}
.status-badge {
  font-size: 10px;
  color: var(--text-faint);
  text-transform: capitalize;
}

.btn {
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 12.5px;
  border-radius: var(--radius-md);
  padding: 8px 14px;
  border: 1px solid var(--border-bright);
  background: var(--surface-raised);
  color: var(--text);
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn--primary {
  background: var(--primary);
  border-color: var(--primary);
  color: white;
}
.btn-link {
  background: transparent;
  border: none;
  color: var(--primary);
  font-size: 11.5px;
  font-weight: 600;
}
</style>
