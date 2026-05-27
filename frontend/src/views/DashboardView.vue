<template>
  <main class="dashboard">
    <section class="hero">

      <h1 class="main-title">
        🌱 Eco Webpage Analytics
      </h1>

      <p class="subtitle">
        Enter a website URL and analyze its estimated carbon impact, resource usage, and optimization opportunities.
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
            {{ result.co2_per_1000_visits }}g
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
                "#2f855a",
                "#68d391",
                "#9ae6b4",
                "#c6f6d5",
              ],

              borderWidth: 0,
            },
          ],
        },

        options: {
          responsive: true,

          plugins: {
            legend: {
              position: "bottom",
            },
          },
        },
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
  padding: 48px 24px;
  background: #f4f7f6;
  color: #1f2933;
}

.hero {
  max-width: 900px;
  margin: 0 auto 32px;
  padding: 48px 40px;
  border-radius: 24px;
  background: linear-gradient(135deg, #ffffff, #eaf7ef);
  box-shadow: 0 20px 50px rgba(31, 41, 51, 0.08);

  text-align: center;
}

.main-title {
  margin: 0;
  font-size: 42px;
  font-weight: 800;
  color: #1f2933;
}

.subtitle {
  max-width: 680px;
  margin: 18px auto 32px;
  color: #5b6773;
  font-size: 15px;
  line-height: 1.6;
}

.url-form {
  display: flex;
  gap: 12px;
}

.url-form input {
  flex: 1;
  padding: 15px 16px;
  border: 1px solid #d8e0dd;
  border-radius: 14px;
  font-size: 15px;
  outline: none;
}

.url-form input:focus {
  border-color: #2f855a;
}

.url-form button {
  padding: 0 24px;
  border: none;
  border-radius: 14px;
  background: #2f855a;
  color: white;
  font-weight: 700;
  cursor: pointer;
}

.url-form button:hover {
  background: #276749;
}

.results {
  max-width: 900px;
  margin: 0 auto;
}

.score-card,
.metric-card,
.panel {
  background: white;
  border-radius: 20px;
  box-shadow: 0 12px 30px rgba(31, 41, 51, 0.07);
}

.score-card {
  padding: 28px;
  margin-bottom: 20px;
}

.rating-top {
  display: flex;
  align-items: center;
  gap: 28px;
  margin-bottom: 22px;
}

.rating-current {
  min-width: 120px;
}

.card-label {
  margin: 0 0 8px;
  color: #6b7280;
  font-weight: 700;
}

.score-card h2 {
  margin: 4px 0 0;
  font-size: 56px;
  color: #2f855a;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}

.metric-card {
  padding: 20px;
}

.metric-card p {
  margin: 0 0 8px;
  color: #6b7280;
  font-size: 14px;
}

.metric-card h3 {
  margin: 0;
  font-size: 22px;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.panel {
  padding: 28px;
}

.panel h2 {
  margin: 0 0 20px;
}

.breakdown-item {
  margin-bottom: 20px;
}

.breakdown-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.progress {
  height: 10px;
  border-radius: 999px;
  background: #e5e7eb;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 999px;
  background: #2f855a;
}

.breakdown-item small {
  display: block;
  margin-top: 6px;
  color: #6b7280;
}

.recommendations {
  padding-left: 20px;
  margin: 0;
}

.recommendations li {
  margin-bottom: 12px;
  color: #374151;
  line-height: 1.5;
}

.error-message {
  margin: 14px 0 0;
  color: #c53030;
  font-weight: 600;
}

.url-form button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: white;
  border-radius: 50%;
  display: inline-block;
  margin-right: 8px;
  animation: spin 0.7s linear infinite;
  vertical-align: middle;
}

.chart-container {
  margin-top: 32px;
}

.rating-value {
  font-size: 64px;
  font-weight: 800;
  color: #2f855a;
  line-height: 1;
}

.rating-info {
  padding-left: 28px;
  border-left: 1px solid #e5e7eb;
  color: #374151;
  font-size: 15px;
  line-height: 1.5;
}

.rating-info p {
  margin: 0 0 4px;
}

.rating-scale {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  overflow: hidden;
}

.rating-item {
  padding: 16px 10px;
  text-align: center;
  border-right: 1px solid #e5e7eb;
}

.rating-item:last-child {
  border-right: none;
}

.rating-item.active {
  background: #eaf7ef;
}

.rating-item strong {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  margin-bottom: 10px;
  border-radius: 50%;
  color: white;
  font-size: 18px;
}

.rating-item:nth-child(1) strong {
  background: #2f855a;
}

.rating-item:nth-child(2) strong {
  background: #48bb78;
}

.rating-item:nth-child(3) strong {
  background: #ecc94b;
}

.rating-item:nth-child(4) strong {
  background: #ed8936;
}

.rating-item:nth-child(5) strong {
  background: #f56565;
}

.rating-item:nth-child(6) strong {
  background: #e53e3e;
}

.rating-item span {
  display: block;
  margin-bottom: 8px;
  color: #374151;
  font-size: 14px;
}

.rating-item small {
  display: block;
  color: #374151;
  font-size: 13px;
  line-height: 1.3;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 800px) {
  .url-form,
  .score-card {
    flex-direction: column;
    align-items: stretch;
  }

  .metrics-grid,
  .content-grid {
    grid-template-columns: 1fr;
  }

  .main-title {
    font-size: 32px;
  }

  .rating-top {
    flex-direction: column;
    align-items: flex-start;
  }

  .rating-info {
    padding-left: 0;
    border-left: none;
  }

  .rating-scale {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>