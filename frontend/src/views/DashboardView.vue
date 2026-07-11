<template>
  <main class="dashboard">
    <section class="hero">

      <div class="brand-logo">
        <img
            src="@/assets/logo2.png"
            alt="EcoWeb logo"
            class="brand-logo-image"
        />

        <h1 class="main-title">
          Eco<span>Web</span>
        </h1>
      </div>

      <p class="subtitle">
        Enter a website URL and analyze its estimated carbon footprint.
      </p>

      <form class="url-form" @submit.prevent="analyzeWebsite">
        <input
            v-model="url"
            type="text"
            placeholder="https://example.com"
        />

        <button type="submit" :disabled="loading">

          <span v-if="loading" class="spinner"></span>

          {{ loading ? "Analyzing..." : "Analyze" }}

        </button>
      </form>

      <p v-if="error" class="error-message">
        {{ error }}
      </p>

    </section>

    <section v-if="result" class="results">
      <div class="score-card">
        <div class="rating-top">
          <div class="rating-current">
            <p class="card-label">Carbon Rating</p>
            <div class="rating-value">{{ result.rating }}</div>
          </div>

          <div class="rating-info">
            <p>This rating reflects the estimated carbon emissions per visit.</p>
            <p>Lower emissions mean a better rating.</p>
          </div>
        </div>

        <div class="rating-scale">
          <div
              v-for="item in ratingScale"
              :key="item.grade"
              class="rating-item"
              :class="{ active: result.rating === item.grade }"
          >
            <strong>{{ item.grade }}</strong>
            <span>{{ item.range }}</span>
            <small>{{ item.label }}</small>
          </div>
        </div>
      </div>

      <div class="metrics-grid">
        <div class="metric-card">
          <p>CO₂ per visit</p>

          <h3>
            {{ result.co2_per_visit }}g
          </h3>

        </div>

        <div class="metric-card">
          <p>CO₂ per 1000 visits</p>

          <h3>
            {{ Number(result.co2_per_1000_visits).toFixed(2) }}g
          </h3>

        </div>

        <div class="metric-card">
          <p>Total page size</p>
          <h3>{{ formatBytes(result.total_bytes) }}</h3>
        </div>

        <div class="metric-card">
          <p>Requests</p>
          <h3>{{ result.requests }}</h3>
        </div>

        <div class="metric-card">
          <p>Load time</p>
          <h3>{{ result.load_time }}s</h3>
        </div>
      </div>

      <div class="content-grid">
        <div class="panel">
          <h2>Resource Breakdown</h2>

          <div
              v-for="item in breakdown"
              :key="item.name"
              class="breakdown-item"
          >
            <div class="breakdown-header">
              <span>{{ item.name }}</span>
              <strong>{{ item.percentage }}%</strong>
            </div>

            <div class="progress">
              <div
                  class="progress-fill"
                  :style="{ width: item.percentage + '%' }"
              ></div>
            </div>

            <small>{{ formatBytes(item.bytes) }}</small>
          </div>

          <div class="chart-container">
            <canvas ref="breakdownChart"></canvas>
          </div>
        </div>

        <div class="panel">
          <h2>Recommendations</h2>

          <ul class="recommendations">
            <li
                v-for="recommendation in recommendations"
                :key="recommendation"
            >
              {{ recommendation }}
            </li>
          </ul>
        </div>
      </div>
    </section>
  </main>
</template>

<script>
import Chart from "chart.js/auto"
export default {
  name: "DashboardView",

  data() {
    return {
      url: "",
      result: null,
      loading: false,
      error: "",
      chart: null,
    }
  },

  computed: {
    breakdown() {
      if (!this.result) {
        return []
      }

      const total = this.result.total_bytes || 1

      return [
        {
          name: "Images",
          bytes: this.result.images_bytes,
          percentage: Math.round((this.result.images_bytes / total) * 100),
        },
        {
          name: "JavaScript",
          bytes: this.result.js_bytes,
          percentage: Math.round((this.result.js_bytes / total) * 100),
        },
        {
          name: "CSS",
          bytes: this.result.css_bytes,
          percentage: Math.round((this.result.css_bytes / total) * 100),
        },
        {
          name: "Other",
          bytes:
              this.result.total_bytes -
              this.result.images_bytes -
              this.result.js_bytes -
              this.result.css_bytes,
          percentage: Math.round(
              ((this.result.total_bytes -
                      this.result.images_bytes -
                      this.result.js_bytes -
                      this.result.css_bytes) /
                  total) *
              100
          ),
        }
      ]
    },

    ratingScale() {
      return [
        { grade: "A", range: "< 0.05g", label: "Very low emissions" },
        { grade: "B", range: "0.05 – 0.10g", label: "Low emissions" },
        { grade: "C", range: "0.10 – 0.20g", label: "Moderate emissions" },
        { grade: "D", range: "0.20 – 0.30g", label: "High emissions" },
        { grade: "E", range: "0.30 – 0.40g", label: "Very high emissions" },
        { grade: "F", range: "> 0.40g", label: "Extremely high emissions" },
      ]
    },

    recommendations() {
      if (!this.result) {
        return []
      }

      const items = []
      const total = this.result.total_bytes || 1

      const imageShare = this.result.images_bytes / total
      const jsShare = this.result.js_bytes / total
      const cssShare = this.result.css_bytes / total

      if (imageShare > 0.5) {
        items.push("Images make up more than 50% of the page size. Compress images and consider WebP or AVIF formats.")
      }

      if (jsShare > 0.3) {
        items.push("JavaScript is a large part of the page size. Minify scripts, remove unused code, or use lazy loading.")
      }

      if (cssShare > 0.15) {
        items.push("CSS size is relatively high. Remove unused styles and minify CSS files.")
      }

      if (this.result.requests > 80) {
        items.push("The page sends many HTTP requests. Reduce third-party scripts and bundle smaller assets where possible.")
      }

      if (this.result.load_time > 3) {
        items.push("Load time is above 3 seconds. Optimize critical resources and improve server response time.")
      }

      if (this.result.co2_per_visit > 0.4) {
        items.push("Estimated CO₂ per visit is high. Reducing page weight and load time should lower the footprint.")
      }

      if (items.length === 0) {
        items.push("The page looks reasonably optimized based on the collected metrics.")
      }

      return items
    }
  },

  methods: {
    saveUrl() {
      localStorage.setItem("saved-url", this.url)
    },
    renderChart() {

      if (!this.result) return

      if (this.chart) {
        this.chart.destroy()
      }

      this.chart = new Chart(this.$refs.breakdownChart, {
        type: "doughnut",

        data: {
          labels: this.breakdown.map(item => item.name),

          datasets: [
            {
              data: this.breakdown.map(item => item.bytes),

              backgroundColor: [
                "#22c55e", // Images
                "#4ade80", // JavaScript
                "#86efac", // CSS
                "#334155", // Other
              ],

              borderColor: "#1e293b",
              borderWidth: 3,
              hoverBorderWidth: 4,
              hoverOffset: 10
            }
          ]
        },

        options: {
          responsive: true,
          maintainAspectRatio: false,

          cutout: "72%",

          plugins: {

            legend: {
              position: "bottom",

              labels: {
                color: "#e2e8f0",
                padding: 22,
                boxWidth: 16,
                boxHeight: 16,
                usePointStyle: true,
                pointStyle: "circle",

                font: {
                  size: 13,
                  weight: "600"
                }
              }
            },

            tooltip: {
              backgroundColor: "#162133",
              titleColor: "#ffffff",
              bodyColor: "#cbd5e1",
              borderColor: "#22c55e",
              borderWidth: 1,
              padding: 12,

              callbacks: {
                label: (context) => {
                  const value = this.breakdown[context.dataIndex]

                  return `${value.name}: ${this.formatBytes(value.bytes)} (${value.percentage}%)`
                }
              }
            }

          },

          animation: {
            duration: 900,
            easing: "easeOutQuart"
          }
        }
      })
    },

    async analyzeWebsite() {

      this.loading = true

      try {

        this.saveUrl()

        const response = await fetch("http://127.0.0.1:8000/api/analyze", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            url: this.url,
          }),
        })

        this.result = await response.json()

        this.$nextTick(() => {
          this.renderChart()
        })

      } finally {
        this.loading = false
      }
    },

    formatBytes(bytes) {
      if (!bytes) {
        return "0 KB"
      }

      const mb = bytes / 1024 / 1024

      if (mb >= 1) {
        return `${mb.toFixed(2)} MB`
      }

      return `${(bytes / 1024).toFixed(1)} KB`
    },
  },

  mounted() {
    const savedUrl = localStorage.getItem("saved-url")

    if (savedUrl) {
      this.url = savedUrl
    }
  },
}
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  padding: 50px 30px;
  background:
      radial-gradient(circle at top right, #1f5f46 0%, transparent 35%),
      radial-gradient(circle at bottom left, #143a30 0%, transparent 40%),
      #0f172a;
  color: #f8fafc;
  font-family: Inter, sans-serif;
}

.hero,
.results {
  width: 100%;
  max-width: 1200px;
  margin-left: auto;
  margin-right: auto;
  box-sizing: border-box;
}

.hero {
  margin-bottom: 35px;
  padding: 45px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(18px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow:
      0 20px 60px rgba(0, 0, 0, 0.45),
      inset 0 1px 0 rgba(255, 255, 255, 0.05);
  text-align: center;
}

.results {
  margin-top: 0;
}

.brand-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  margin-bottom: 8px;
}

.brand-logo-image {
  width: 48px;
  height: 48px;
  object-fit: contain;
  flex-shrink: 0;
  filter: drop-shadow(0 0 12px rgba(74, 222, 128, 0.28));
}

.main-title {
  margin: 0;
  font-size: 48px;
  font-weight: 800;
  letter-spacing: -1.5px;
  line-height: 1;
  color: #ffffff;
}

.main-title span {
  color: #4ade80;
}

.subtitle {
  max-width: 760px;
  margin: 18px auto 35px;
  color: #cbd5e1;
  font-size: 16px;
  line-height: 1.7;
}

.url-form {
  display: flex;
  gap: 14px;
}

.url-form input {
  flex: 1;
  min-width: 0;
  padding: 17px 20px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: #162133;
  color: white;
  font-size: 15px;
  transition: 0.25s;
}

.url-form input::placeholder {
  color: #94a3b8;
}

.url-form input:focus {
  outline: none;
  border-color: #22c55e;
  box-shadow: 0 0 0 4px rgba(34, 197, 94, 0.18);
}

.url-form button {
  padding: 0 30px;
  border: none;
  border-radius: 16px;
  background: linear-gradient(135deg, #22c55e, #16a34a);
  color: white;
  font-weight: 700;
  cursor: pointer;
  transition: 0.25s;
  box-shadow: 0 8px 24px rgba(34, 197, 94, 0.35);
}

.url-form button:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 35px rgba(34, 197, 94, 0.45);
}

.url-form button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.score-card,
.metric-card,
.panel {
  box-sizing: border-box;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(18px);
  border-radius: 24px;
  box-shadow: 0 15px 45px rgba(0, 0, 0, 0.35);
  transition: 0.25s;
}

.score-card {
  width: 100%;
  padding: 32px;
  margin-bottom: 22px;
}

.rating-top {
  display: flex;
  gap: 35px;
  align-items: center;
  margin-bottom: 25px;
}

.rating-current {
  flex-shrink: 0;
}

.card-label {
  margin: 0 0 10px;
  color: #94a3b8;
  text-transform: uppercase;
  font-size: 13px;
  letter-spacing: 0.8px;
}

.rating-value {
  font-size: 72px;
  font-weight: 800;
  line-height: 1;
  color: #4ade80;
  text-shadow: 0 0 18px rgba(74, 222, 128, 0.45);
}

.rating-info {
  padding-left: 28px;
  border-left: 1px solid rgba(255, 255, 255, 0.08);
  color: #cbd5e1;
  line-height: 1.7;
}

.rating-info p {
  margin: 0 0 8px;
}

.rating-info p:last-child {
  margin-bottom: 0;
}

.rating-scale {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
}

.rating-item {
  min-width: 0;
  padding: 18px 12px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: #172335;
  text-align: center;
  transition: 0.25s;
}

.rating-item:hover {
  transform: translateY(-3px);
}

.rating-item.active {
  background: linear-gradient(180deg, #1d3d30, #173326);
  border-color: #22c55e;
  box-shadow: 0 0 25px rgba(34, 197, 94, 0.25);
}

.rating-item strong {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  margin: 0 auto 12px;
  border-radius: 50%;
  color: white;
  font-size: 18px;
}

.rating-item:nth-child(1) strong {
  background: #16a34a;
}

.rating-item:nth-child(2) strong {
  background: #22c55e;
}

.rating-item:nth-child(3) strong {
  background: #84cc16;
}

.rating-item:nth-child(4) strong {
  background: #f59e0b;
}

.rating-item:nth-child(5) strong {
  background: #f97316;
}

.rating-item:nth-child(6) strong {
  background: #ef4444;
}

.rating-item span {
  display: block;
  margin-bottom: 7px;
  color: white;
  font-size: 14px;
}

.rating-item small {
  display: block;
  color: #94a3b8;
  line-height: 1.35;
}

.metrics-grid {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 18px;
  margin-bottom: 22px;
}

.metric-card {
  min-width: 0;
  min-height: 124px;
  padding: 24px;
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}

.metric-card:hover {
  transform: translateY(-5px);
  border-color: rgba(34, 197, 94, 0.45);
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.45);
}

.metric-card::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: linear-gradient(90deg, #22c55e, #4ade80);
}

.metric-card p {
  min-height: 38px;
  margin: 0 0 10px;
  color: #94a3b8;
  font-size: 13px;
  line-height: 1.35;
  text-transform: uppercase;
  letter-spacing: 0.8px;
}

.metric-card h3 {
  margin: 0;
  color: white;
  font-size: 26px;
  font-weight: 700;
  line-height: 1.15;
  white-space: nowrap;
}

.content-grid {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 22px;
}

.panel {
  min-width: 0;
  padding: 30px;
}

.panel h2 {
  margin: 0 0 25px;
  color: white;
}

.breakdown-item {
  margin-bottom: 20px;
}

.breakdown-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  color: white;
}

.breakdown-item small {
  display: block;
  margin-top: 6px;
  color: #94a3b8;
}

.progress {
  height: 10px;
  border-radius: 999px;
  background: #223048;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #22c55e, #4ade80);
}

.chart-container {
  margin-top: 35px;
  height: 340px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.recommendations {
  margin: 0;
  padding-left: 20px;
}

.recommendations li {
  margin-bottom: 16px;
  color: #dbe5f1;
  line-height: 1.7;
}

.error-message {
  margin-top: 16px;
  color: #f87171;
  font-weight: 600;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  display: inline-block;
  margin-right: 8px;
  animation: spin 0.7s linear infinite;
  vertical-align: middle;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 900px) {
  .dashboard {
    padding: 30px 18px;
  }

  .hero {
    padding: 34px 24px;
  }

  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .content-grid {
    grid-template-columns: 1fr;
  }

  .rating-scale {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .rating-top {
    flex-direction: column;
    align-items: flex-start;
  }

  .rating-info {
    padding-left: 0;
    border-left: none;
  }

  .url-form {
    flex-direction: column;
  }

  .url-form button {
    min-height: 52px;
  }

  .brand-logo-image {
    width: 40px;
    height: 40px;
  }

  .main-title {
    font-size: 38px;
  }
}
</style>