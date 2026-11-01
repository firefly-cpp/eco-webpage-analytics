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

        <button type="submit" :disabled="loading || recalculating || locations_loading || locations.length === 0">

          <span v-if="loading" class="spinner"></span>

          {{ loading ? "Analyzing..." : "Analyze" }}

        </button>
      </form>

      <div class="location-selectors">
        <div class="location-field">
          <label for="visitor-location">Visitor location</label>

          <select
            id="visitor-location"
            v-model="visitor_location"
            @change="recalculateCarbon"
            :disabled="loading || recalculating || locations_loading || locations.length === 0"
          >
            <option
              v-for="location in locations"
              :key="location.location_code"
              :value="location.location_code"
            >
              {{ location.name }}
            </option>
          </select>
        </div>

        <div class="location-field">
          <label for="hosting-location">Hosting location</label>

          <select
            id="hosting-location"
            v-model="hosting_location"
            @change="recalculateCarbon"
            :disabled="loading || recalculating || locations_loading || locations.length === 0"
          >
            <option
              v-for="location in locations"
              :key="location.location_code"
              :value="location.location_code"
            >
              {{ location.name }}
            </option>
          </select>
        </div>
      </div>

      <p
        class="recalculation-status"
        :class="{ visible: recalculating }"
        role="status"
      >
        {{ recalculating ? "Updating carbon estimates..." : "" }}
      </p>
      
      <p v-if="locations_loading">Loading locations...</p>

      <p v-if="locations_error" class="error-message">
        {{ locations_error }}
      </p>

      <p v-if="error" class="error-message">
        {{ error }}
      </p>

    </section>

    <section v-if="currentResult" class="results">
      <div v-if="currentResult.carbon_factors" class="panel scenario-panel">
        <h2>Calculated location scenario</h2>

        <div class="scenario-grid">
          <div>
            <p class="card-label">Visitor location</p>
            <strong>{{ currentResult.carbon_factors.visitor.name }}</strong>

            <p>
              {{ currentResult.carbon_factors.visitor.carbon_intensity }}
              gCO₂e/kWh
            </p>

            <small>
              Data year: {{ currentResult.carbon_factors.visitor.year }}
            </small>
          </div>

          <div>
            <p class="card-label">Hosting location</p>
            <strong>{{ currentResult.carbon_factors.hosting.name }}</strong>

            <p>
              {{ currentResult.carbon_factors.hosting.carbon_intensity }}
              gCO₂e/kWh
            </p>

            <small>
              Data year: {{ currentResult.carbon_factors.hosting.year }}
            </small>
          </div>

          <div>
            <p class="card-label">Network assumption</p>
            <strong>World average</strong>

            <p>
              {{ currentResult.carbon_factors.network.carbon_intensity }}
              gCO₂e/kWh
            </p>

            <small>
              Data year: {{ currentResult.carbon_factors.network.year }}
            </small>
          </div>
        </div>

        <p class="scenario-note">
          Electricity factors: Ember annual generation averages.
          Embodied emissions use a separate model assumption of
          {{ currentResult.carbon_factors.embodied.carbon_intensity }}
          gCO₂e/kWh-equivalent.
        </p>
      </div>

      <div class="view-switcher">
        <button :class="{ 
            active: selectedView === 'baseline' 
          }" @click="selectView('baseline')">
          Initial Load
        </button>

        <button :class="{
            active: selectedView === 'full_scroll'
          }" @click="selectView('full_scroll')">
          Full Scroll
        </button>

        <button :class="{
            active: selectedView === 'without_third_party'
          }" @click="selectView('without_third_party')">
          Without Third Parties
        </button>
      </div>
      <div class="score-card">
        <div class="rating-top">
          <div class="rating-current">
            <p class="card-label">Carbon Rating</p>
            <div
            class="rating-value"
            :style="{
              color: ratingColor(currentResult.rating),
              textShadow: `0 0 18px ${ratingColor(currentResult.rating)}88`
            }"
          >
            {{ currentResult.rating }}
          </div>
          </div>

          <div class="rating-info">
            <p>This rating reflects estimated emissions per visit for the calculated location scenario.</p>
            <p>Lower emissions mean a better rating.</p>
          </div>
        </div>

        <div class="rating-scale">
          <div
              v-for="item in ratingScale"
              :key="item.grade"
              class="rating-item"
              :class="{ active: currentResult.rating === item.grade }"
              :style="currentResult.rating === item.grade
                ? {
                    borderColor: ratingColor(item.grade),
                    boxShadow: `0 0 25px ${ratingColor(item.grade)}66`,
                    background: `linear-gradient(180deg, ${ratingColor(item.grade)}33, ${ratingColor(item.grade)}11)`
                  }
                : {}"
          >
            <strong>{{ item.grade }}</strong>
            <span>{{ item.range }}</span>
            <small>{{ item.label }}</small>
          </div>
        </div>
      </div>

      <div class="metrics-grid">
        <div class="metric-card" :style="metricCardStyle('co2')">
          <p>CO₂ per visit</p>

          <h3>
            {{ currentResult.co2_per_visit }}g
          </h3>

        </div>

        <div class="metric-card" :style="metricCardStyle('co2')">
          <p>CO₂ per 1000 visits</p>

          <h3>
            {{ Number(currentResult.co2_per_1000_visits).toFixed(2) }}g
          </h3>

        </div>

        <div class="metric-card" :style="metricCardStyle('pageSize')">
          <p>Total page size</p>
          <h3>{{ formatBytes(currentResult.total_bytes) }}</h3>
        </div>

        <div class="metric-card" :style="metricCardStyle('requests')">
          <p>Requests</p>
          <h3>{{ currentResult.requests }}</h3>
        </div>

        <div class="metric-card" :style="metricCardStyle('loadTime')">
          <p>Load time</p>
          <h3>{{ currentResult.load_time }}s</h3>
        </div>
      </div>

      <div v-if="currentResult.image_transcoding" class="image-counterfactual">
        <div>
          <p class="card-label">
            Image Optimization Counterfactual
          </p>

          <h2>
            WebP quality {{ currentResult.image_transcoding.quality }}
          </h2>
        </div>

        <div class="counterfactual-values">
          <div>
            <span>Current eligible images</span>
            <strong>
              {{ formatBytes(currentResult.image_transcoding.original_bytes) }}
            </strong>
          </div>

          <div>
            <span>WebP equivalent</span>
            <strong>
              {{ formatBytes(currentResult.image_transcoding.webp_bytes) }}
            </strong>
          </div>

          <div>
            <span>Potential saving</span>
            <strong>
              -{{ formatBytes(currentResult.image_transcoding.saved_bytes) }}
            </strong>
          </div>

          <div>
            <span>CO₂ saving / visit</span>
            <strong>
              -{{ currentResult.image_transcoding.saved_co2_per_visit }}g
            </strong>
          </div>
        </div>
      </div>

      <div v-if="thirdPartyComparison" class="image-counterfactual">
        <div>
          <p class="card-label">
            Third-Party Counterfactual
          </p>

          <h2>
            With vs. without third-party resources (full scroll)
          </h2>
        </div>

        <div class="counterfactual-values">
          <div>
            <span>With third parties</span>
            <strong>{{ formatBytes(thirdPartyComparison.withBytes) }}</strong>
          </div>

          <div>
            <span>Without third parties</span>
            <strong>{{ formatBytes(thirdPartyComparison.withoutBytes) }}</strong>
          </div>

          <div>
            <span>Third-party share</span>
            <strong>
              -{{ formatBytes(thirdPartyComparison.savedBytes) }}
              ({{ thirdPartyComparison.savedPercent }}%)
            </strong>
          </div>

          <div>
            <span>CO₂ saving / visit</span>
            <strong>-{{ thirdPartyComparison.savedCo2 }}g</strong>
          </div>
        </div>
      </div>

      <div v-if="currentResult.carbon_breakdown" class="panel emissions-panel">
        <h2>Emissions breakdown</h2>

        <table class="emissions-table">
          <thead>
            <tr>
            <th scope="col">Component</th>
              <th scope="col">gCO₂e per visit</th>
            </tr>
          </thead>

          <tbody>
            <tr>
              <td>Data-centre operation</td>
              <td>
                {{ formatCo2(currentResult.carbon_breakdown.dc_operational_co2) }}
              </td>
            </tr>

            <tr>
              <td>Network operation</td>
              <td>
                {{ formatCo2(currentResult.carbon_breakdown.network_operational_co2) }}
              </td>
            </tr>

            <tr>
              <td>User-device operation</td>
              <td>
                {{ formatCo2(currentResult.carbon_breakdown.user_device_operational_co2) }}
              </td>
            </tr>

            <tr class="subtotal-row">
              <td>Operational subtotal</td>
              <td>
                {{ formatCo2(currentResult.carbon_breakdown.operational_co2) }}
              </td>
            </tr>

            <tr>
              <td>Embodied emissions</td>
              <td>
                {{ formatCo2(currentResult.carbon_breakdown.embodied_co2) }}
              </td>
            </tr>

            <tr class="total-row">
              <td>Total</td>
              <td>
                {{ formatCo2(currentResult.carbon_breakdown.total_co2) }}
              </td>
            </tr>
          </tbody>
        </table>

        <p class="scenario-note">
          Total emissions = operational subtotal + embodied emissions.
          Embodied emissions represent allocated equipment manufacturing impacts.
        </p>
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
              <strong :style="{ color: resourceColor(item) }">
              {{ item.percentage }}%
            </strong>
            </div>

            <div class="progress">
              <div
                class="progress-fill"
                :style="{
                  width: item.percentage + '%',
                  background: `linear-gradient(90deg, ${resourceColor(item)}, ${resourceColor(item)}aa)`
                }"
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
      selectedView: "baseline",
      loading: false,
      error: "",
      chart: null,
      locations: [],
      visitor_location: "WORLD",
      hosting_location: "WORLD",
      locations_loading: true,
      locations_error: "",
      recalculating: false,
    }
  },

  computed: {
    currentResult() {
      if (!this.result || !this.result[this.selectedView]) {
        return null
      }

      return this.result[this.selectedView]
    },

    thirdPartyComparison() {
      if (!this.result || !this.result.full_scroll || !this.result.without_third_party) {
        return null
      }

      const withThirdParty = this.result.full_scroll
      const withoutThirdParty = this.result.without_third_party

      const savedBytes = Math.max(0, withThirdParty.total_bytes - withoutThirdParty.total_bytes)
      const savedCo2 = Math.max(0, withThirdParty.co2_per_visit - withoutThirdParty.co2_per_visit)

      return {
        withBytes: withThirdParty.total_bytes,
        withoutBytes: withoutThirdParty.total_bytes,
        savedBytes,
        savedPercent: withThirdParty.total_bytes
            ? Math.round((savedBytes / withThirdParty.total_bytes) * 100)
            : 0,
        savedCo2: savedCo2.toFixed(4)
      }
    },

    breakdown() {
      if (!this.currentResult) {
        return []
      }

      const total = this.currentResult.total_bytes || 1

      return [
        {
          name: "Images",
          bytes: this.currentResult.images_bytes,
          percentage: Math.round((this.currentResult.images_bytes / total) * 100),
        },
        {
          name: "JavaScript",
          bytes: this.currentResult.js_bytes,
          percentage: Math.round((this.currentResult.js_bytes / total) * 100),
        },
        {
          name: "CSS",
          bytes: this.currentResult.css_bytes,
          percentage: Math.round((this.currentResult.css_bytes / total) * 100),
        },
        {
          name: "Other",
          bytes:
              this.currentResult.total_bytes -
              this.currentResult.images_bytes -
              this.currentResult.js_bytes -
              this.currentResult.css_bytes,
          percentage: Math.round(
              ((this.currentResult.total_bytes -
                      this.currentResult.images_bytes -
                      this.currentResult.js_bytes -
                      this.currentResult.css_bytes) /
                  total) *
              100
          ),
        }
      ]
    },

    ratingScale() {
      return [
        { grade: "A+", range: "≤ 0.040g", label: "Best performance" },
        { grade: "A", range: "0.041 – 0.079g", label: "Very low emissions" },
        { grade: "B", range: "0.080 – 0.145g", label: "Low emissions" },
        { grade: "C", range: "0.146 – 0.209g", label: "Moderate emissions" },
        { grade: "D", range: "0.210 – 0.278g", label: "High emissions" },
        { grade: "E", range: "0.279 – 0.359g", label: "Very high emissions" },
        { grade: "F", range: "> 0.359g", label: "Extremely high emissions" },
      ]
    },

    recommendations() {
      if (!this.currentResult) {
        return []
      }

      const items = []
      const total = this.currentResult.total_bytes || 1

      const imageBytes = this.currentResult.images_bytes || 0
      const jsBytes = this.currentResult.js_bytes || 0
      const cssBytes = this.currentResult.css_bytes || 0

      const imageShare = imageBytes / total
      const jsShare = jsBytes / total
      const cssShare = cssBytes / total

      if (imageBytes > this.mb(1.5) || (imageShare > 0.5 && imageBytes > this.kb(500))) {
        items.push("Images are a large part of the page size. Compress images and consider WebP or AVIF formats.")
      }

      if (jsBytes > this.mb(1) || (jsShare > 0.4 && jsBytes > this.kb(300))) {
        items.push("JavaScript is a large part of the page size. Minify scripts, remove unused code, or use lazy loading.")
      }

      if (cssBytes > this.kb(250) || (cssShare > 0.2 && cssBytes > this.kb(120))) {
        items.push("CSS size is relatively high. Remove unused styles and minify CSS files.")
      }

      if (this.currentResult.requests > 80) {
        items.push("The page sends many HTTP requests. Reduce third-party scripts and bundle smaller assets where possible.")
      }

      if (this.currentResult.load_time > 3) {
        items.push("Load time is above 3 seconds. Optimize critical resources and improve server response time.")
      }

      if (this.currentResult.co2_per_visit > 0.359) {
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

    selectView(view) {
      this.selectedView = view
      this.$nextTick(() => {
        this.renderChart()
      })
    },

    async loadLocations() {
      this.locations_loading = true
      this.locations_error = ""

      try {
        const response = await fetch(
          "http://127.0.0.1:8000/api/locations"
        )

        if (!response.ok) {
          throw new Error("Could not load the available locations.")
        }

        const locations = await response.json()

        if (!Array.isArray(locations) || locations.length === 0) {
          throw new Error("No locations are available.")
        }

        const worldLocation = locations.find(
          location => location.location_code === "WORLD"
        )

        if (!worldLocation) {
          throw new Error("The dataset does not contain a World average.")
        }

        this.locations = locations

      } catch (error) {
        this.locations = []
        this.locations_error =
          error.message || "Could not load the available locations."

      } finally {
        this.locations_loading = false
      }
    },

    formatCo2(value) {
        if (typeof value !== "number" || !Number.isFinite(value)) {
          return "—"
        }

        return value.toFixed(6)
    },

    async recalculateCarbon() {
      if (!this.result || this.loading || this.recalculating) {
        return
      }

      const previousVisitor =
        this.result.baseline.carbon_factors.visitor.location_code

      const previousHosting =
        this.result.baseline.carbon_factors.hosting.location_code

      this.recalculating = true
      this.error = ""

      try {
        const response = await fetch(
          "http://127.0.0.1:8000/api/recalculate",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              url: this.result.url,
              visitor_location: this.visitor_location,
              hosting_location: this.hosting_location,
              baseline: this.result.baseline,
              full_scroll: this.result.full_scroll,
              without_third_party: this.result.without_third_party,
            }),
          }
        )

        const data = await response.json()

        if (!response.ok) {
          throw new Error("Could not recalculate the carbon estimates.")
        }

        this.result = data

      } catch (error) {
        this.visitor_location = previousVisitor
        this.hosting_location = previousHosting

        this.error = error.message || "Could not recalculate the carbon estimates."

      } finally {
        this.recalculating = false
      }
    },

    renderChart() {

      if (!this.currentResult) return

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

              backgroundColor: this.breakdown.map(item => this.resourceColor(item)),

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

      if (this.loading || this.recalculating) {
        return
      }

      if (this.locations_loading || this.locations.length === 0) {
        this.error = "Please wait until the locations have loaded."
        return
      }

      this.loading = true
      this.error = ""
      this.result = null

      try {

        this.saveUrl()

        const response = await fetch("http://127.0.0.1:8000/api/analyze", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            url: this.url,
            visitor_location: this.visitor_location,
            hosting_location: this.hosting_location,
          }),
        })

        const data = await response.json()

        if (!response.ok) {
          throw new Error(
            data.detail || "The website could not be analyzed."
          )
        }

        this.result = data
        this.selectedView = "baseline"

        this.$nextTick(() => {
          this.renderChart()
        })

      } catch (error) {
        this.error = error.message || "Failed to analyze the website."
        this.result = null

      } finally {
        this.loading = false
      }
    },

    ratingColor(rating) {
      const colors = {
        "A+": "#2f855a",
        A: "#16a34a",
        B: "#22c55e",
        C: "#84cc16",
        D: "#f59e0b",
        E: "#f97316",
        F: "#ef4444",
      }

      return colors[rating] || "#22c55e"
    },

    metricColor(metric) {
      if (!this.currentResult) {
        return "#22c55e"
      }

      if (metric === "co2") {
        return this.ratingColor(this.currentResult.rating)
      }

      if (metric === "pageSize") {
        const mb = (this.currentResult.total_bytes || 0) / 1024 / 1024

        if (mb <= 2) return "#22c55e"
        if (mb <= 5) return "#84cc16"
        if (mb <= 8) return "#f59e0b"
        return "#ef4444"
      }

      if (metric === "requests") {
        const requests = this.currentResult.requests || 0

        if (requests <= 80) return "#22c55e"
        if (requests <= 150) return "#84cc16"
        if (requests <= 300) return "#f59e0b"
        return "#ef4444"
      }

      if (metric === "loadTime") {
        const loadTime = this.currentResult.load_time || 0

        if (loadTime <= 3) return "#22c55e"
        if (loadTime <= 5) return "#84cc16"
        if (loadTime <= 8) return "#f59e0b"
        return "#ef4444"
      }

      return "#22c55e"
    },

    kb(value) {
      return value * 1024
    },

    mb(value) {
      return value * 1024 * 1024
    },

    metricCardStyle(metric) {
      const color = this.metricColor(metric)

      return {
        "--metric-color": color,
        "--metric-color-soft": `${color}88`,
        borderColor: `${color}55`,
      }
    },

    resourceColor(item) {
      const bytes = item.bytes || 0
      const percentage = item.percentage || 0

      if (item.name === "Images") {
        if (bytes > this.mb(1.5) || (percentage > 50 && bytes > this.kb(500))) {
          return "#ef4444"
        }

        if (bytes > this.kb(750) || (percentage > 35 && bytes > this.kb(250))) {
          return "#f59e0b"
        }

        return "#22c55e"
      }

      if (item.name === "JavaScript") {
        if (bytes > this.mb(1) || (percentage > 40 && bytes > this.kb(300))) {
          return "#ef4444"
        }

        if (bytes > this.kb(500) || (percentage > 25 && bytes > this.kb(150))) {
          return "#f59e0b"
        }

        return "#22c55e"
      }

      if (item.name === "CSS") {
        if (bytes > this.kb(250) || (percentage > 20 && bytes > this.kb(120))) {
          return "#ef4444"
        }

        if (bytes > this.kb(150) || (percentage > 12 && bytes > this.kb(80))) {
          return "#f59e0b"
        }

        return "#22c55e"
      }

      if (item.name === "Other") {
        if (bytes > this.mb(1.5) || (percentage > 50 && bytes > this.kb(750))) {
          return "#f59e0b"
        }

        return "#64748b"
      }

      return "#22c55e"
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
    this.loadLocations()

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
  grid-template-columns: repeat(7, minmax(0, 1fr));
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
  transform: translateY(-3px);
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
  background: #2f855a; /* A+ */
}

.rating-item:nth-child(2) strong {
  background: #16a34a;
}

.rating-item:nth-child(3) strong {
  background: #22c55e;
}

.rating-item:nth-child(4) strong {
  background: #84cc16;
}

.rating-item:nth-child(5) strong {
  background: #f59e0b;
}

.rating-item:nth-child(6) strong {
  background: #f97316;
}

.rating-item:nth-child(7) strong {
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

.metric-card {
  --metric-color: #22c55e;
  --metric-color-soft: #4ade80;
  /* ...ostala postojeća svojstva ostaju kako jesu... */
}

.metric-card:hover {
  transform: translateY(-5px);
  border-color: var(--metric-color, #22c55e);
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.45);
}

.metric-card::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: linear-gradient(
      90deg,
      var(--metric-color, #22c55e),
      var(--metric-color-soft, #4ade80)
  );
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

.view-switcher {
  display: flex;
  gap: 10px;
  margin-bottom: 22px;
  padding: 6px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.view-switcher button {
  flex: 1;
  padding: 14px 18px;
  border: 1px solid transparent;
  border-radius: 12px;
  background: transparent;
  color: #94a3b8;
  font-weight: 700;
  cursor: pointer;
  transition: 0.25s;
}

.view-switcher button:hover {
  color: white;
  background: rgba(255, 255, 255, 0.05);
}

.view-switcher button.active {
  color: white;
  background: rgba(34, 197, 94, 0.16);
  border-color: #22c55e;
  box-shadow: 0 0 20px rgba(34, 197, 94, 0.15);
}

.image-counterfactual {
  margin-bottom: 22px;
  padding: 30px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(18px);
  box-shadow: 0 15px 45px rgba(0, 0, 0, 0.35);
}

.image-counterfactual h2 {
  margin: 0 0 24px;
}

.counterfactual-values {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.counterfactual-values div {
  padding: 18px;
  border-radius: 14px;
  background: #172335;
}

.counterfactual-values span {
  display: block;
  margin-bottom: 8px;
  color: #94a3b8;
  font-size: 13px;
}

.counterfactual-values strong {
  color: #ffffff;
  font-size: 20px;
}

.location-selectors {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin-top: 20px;
}

.location-field {
  min-width: 0;
  text-align: left;
}

.location-field label {
  display: block;
  margin-bottom: 8px;
  color: #cbd5e1;
  font-size: 14px;
}

.location-field select {
  box-sizing: border-box;
  width: 100%;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: #162133;
  color: white;
  font-size: 15px;
}

.location-field select:focus {
  outline: none;
  border-color: #22c55e;
}

.location-field select:disabled {
  opacity: 0.6;
}

.scenario-panel,
.emissions-panel {
  margin-bottom: 22px;
}

.scenario-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
}

.scenario-grid strong {
  font-size: 18px;
}

.scenario-grid p {
  color: #cbd5e1;
}

.scenario-grid small {
  color: #94a3b8;
}

.scenario-note {
  margin: 20px 0 0;
  color: #94a3b8;
  font-size: 13px;
  line-height: 1.6;
}

.emissions-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.emissions-table th,
.emissions-table td {
  padding: 14px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  text-align: left;
}

.emissions-table th {
  color: #94a3b8;
}

.emissions-table th:last-child,
.emissions-table td:last-child {
  text-align: right;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.subtotal-row {
  background: rgba(255, 255, 255, 0.04);
  font-weight: 600;
}

.total-row {
  background: rgba(34, 197, 94, 0.1);
  color: #4ade80;
  font-weight: 700;
}

.recalculation-status {
  min-height: 20px;
  margin: 10px 0 0;
  font-size: 13px;
  line-height: 20px;
  color: #94a3b8;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.recalculation-status.visible {
  opacity: 1;
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

  .view-switcher {
    flex-direction: column;
  }

  .counterfactual-values {
    grid-template-columns: 1fr;
  }

  .location-selectors {
  grid-template-columns: 1fr;
  }

  .scenario-grid {
  grid-template-columns: 1fr;
  }
}


</style>