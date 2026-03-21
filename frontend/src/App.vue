<script setup lang="ts">
import { onMounted, ref } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet.heat'
import axios from 'axios'

const mapContainer = ref<HTMLDivElement>()
const categories = ref<{ category: string; count: number }[]>([])
const selectedCategory = ref('')
const showHeatmap = ref(false)
const drawMode = ref(false)
const selectedCount = ref<number | null>(null)
const showTrajectory = ref(false)
const isPlaying = ref(false)
const playProgress = ref(0)
const classifyInput = ref('')
const classifyResult = ref<{category: string, confidence: number} | null>(null)
const searchQuery = ref('')
const searchResult = ref<{total: number, detected_category: string | null} | null>(null)
const isSearching = ref(false)

async function naturalSearch() {
  if (!searchQuery.value.trim()) return
  isSearching.value = true
  const res = await axios.get('http://localhost:8000/api/search', {
    params: { q: searchQuery.value }
  })
  const data = res.data
  searchResult.value = { total: data.total, detected_category: data.detected_category }

  if (geojsonLayer) map.removeLayer(geojsonLayer)
  if (heatLayer) map.removeLayer(heatLayer)

  geojsonLayer = L.geoJSON(data, {
    pointToLayer(feature, latlng) {
      const color = categoryColors[feature.properties.category] ?? '#95a5a6'
      return L.circleMarker(latlng, {
        radius: 8, fillColor: color,
        color: '#fff', weight: 2, fillOpacity: 1
      })
    },
    onEachFeature(feature, layer) {
      const p = feature.properties
      layer.bindPopup(`<b>${p.name}</b><br/>${p.category}`)
    }
  }).addTo(map)

  if (data.features.length > 0) {
    map.fitBounds(geojsonLayer!.getBounds(), { padding: [40, 40] })
  }
  isSearching.value = false
}

function clearSearch() {
  searchQuery.value = ''
  searchResult.value = null
  applyFilter()
}

let map: L.Map
let geojsonLayer: L.GeoJSON | null = null
let heatLayer: any = null
let selectionRect: L.Rectangle | null = null
let allFeatures: any[] = []
let trajectoryLine: L.Polyline | null = null
let trajectoryMarker: L.CircleMarker | null = null
let trajectoryCoords: [number, number][] = []
let animationFrame: number | null = null
let currentStep = 0

const categoryColors: Record<string, string> = {
  '餐饮': '#e74c3c', '医疗': '#3498db', '教育': '#2ecc71',
  '交通': '#f39c12', '景点': '#9b59b6', '购物': '#1abc9c',
  '住宿': '#e67e22', '其他': '#95a5a6',
}

function renderFeatures(features: any[]) {
  if (geojsonLayer) map.removeLayer(geojsonLayer)
  if (heatLayer) map.removeLayer(heatLayer)
  const heatPoints = features.map((f: any) => [
    f.geometry.coordinates[1], f.geometry.coordinates[0], 0.6
  ])
  heatLayer = (L as any).heatLayer(heatPoints, { radius: 20, blur: 15 })
  geojsonLayer = L.geoJSON({ type: 'FeatureCollection', features } as any, {
    pointToLayer(feature, latlng) {
      const color = categoryColors[feature.properties.category] ?? '#95a5a6'
      return L.circleMarker(latlng, {
        radius: 6, fillColor: color, color: '#fff', weight: 1, fillOpacity: 0.85
      })
    },
    onEachFeature(feature, layer) {
      const p = feature.properties
      layer.bindPopup(`
        <div style="min-width:140px">
          <b style="font-size:14px">${p.name}</b><br/>
          <span style="color:#666;font-size:12px">分类：${p.category}</span>
          ${p.address ? `<br/><span style="color:#666;font-size:12px">${p.address}</span>` : ''}
        </div>
      `)
    }
  })
  if (showHeatmap.value) {
    heatLayer.addTo(map)
  } else {
    geojsonLayer.addTo(map)
  }
}

function applyFilter() {
  let filtered = allFeatures
  if (selectedCategory.value) {
    filtered = filtered.filter(f => f.properties.category === selectedCategory.value)
  }
  if (selectionRect) {
    const bounds = selectionRect.getBounds()
    filtered = filtered.filter(f => {
      const [lng, lat] = f.geometry.coordinates
      return bounds.contains([lat, lng])
    })
    selectedCount.value = filtered.length
  } else {
    selectedCount.value = null
  }
  renderFeatures(filtered)
}

function toggleHeatmap() {
  showHeatmap.value = !showHeatmap.value
  if (!geojsonLayer || !heatLayer) return
  if (showHeatmap.value) {
    map.removeLayer(geojsonLayer)
    heatLayer.addTo(map)
  } else {
    map.removeLayer(heatLayer)
    geojsonLayer.addTo(map)
  }
}

function selectCategory(cat: string) {
  selectedCategory.value = cat === selectedCategory.value ? '' : cat
  applyFilter()
}

function clearSelection() {
  if (selectionRect) map.removeLayer(selectionRect)
  selectionRect = null
  selectedCount.value = null
  drawMode.value = false
  map.dragging.enable()
  map.getContainer().style.cursor = ''
  applyFilter()
}

function toggleDraw() {
  if (drawMode.value) { clearSelection(); return }
  drawMode.value = true
  map.dragging.disable()
  map.getContainer().style.cursor = 'crosshair'
  let startLatLng: L.LatLng | null = null
  let tempRect: L.Rectangle | null = null
  function onMouseDown(e: L.LeafletMouseEvent) { startLatLng = e.latlng }
  function onMouseMove(e: L.LeafletMouseEvent) {
    if (!startLatLng) return
    if (tempRect) map.removeLayer(tempRect)
    tempRect = L.rectangle(L.latLngBounds(startLatLng, e.latlng), {
      color: '#4a90e2', weight: 2, fillOpacity: 0.15, dashArray: '5,5'
    }).addTo(map)
  }
  function onMouseUp(e: L.LeafletMouseEvent) {
    if (!startLatLng) return
    map.off('mousedown', onMouseDown)
    map.off('mousemove', onMouseMove)
    map.off('mouseup', onMouseUp)
    map.dragging.enable()
    map.getContainer().style.cursor = ''
    drawMode.value = false
    if (selectionRect) map.removeLayer(selectionRect)
    selectionRect = tempRect
    tempRect = null
    startLatLng = null
    applyFilter()
  }
  map.on('mousedown', onMouseDown)
  map.on('mousemove', onMouseMove)
  map.on('mouseup', onMouseUp)
}

async function toggleTrajectory() {
  showTrajectory.value = !showTrajectory.value
  if (!showTrajectory.value) {
    stopAnimation()
    if (trajectoryLine) map.removeLayer(trajectoryLine)
    if (trajectoryMarker) map.removeLayer(trajectoryMarker)
    trajectoryLine = null
    trajectoryMarker = null
    return
  }
  const res = await axios.get('http://localhost:8000/api/trajectories')
  const features = res.data.features
  if (!features.length) return
  const coords = features[0].geometry.coordinates
  trajectoryCoords = coords.map((c: number[]) => [c[1], c[0]] as [number, number])
  trajectoryLine = L.polyline(trajectoryCoords, {
    color: '#f39c12', weight: 3, opacity: 0.8, dashArray: '8,4'
  }).addTo(map)
  trajectoryMarker = L.circleMarker(trajectoryCoords[0]!, {
    radius: 8, fillColor: '#f39c12', color: '#fff', weight: 2, fillOpacity: 1
  }).addTo(map)
  map.fitBounds(trajectoryLine.getBounds(), { padding: [40, 40] })
  currentStep = 0
  playProgress.value = 0
}

function stopAnimation() {
  if (animationFrame) cancelAnimationFrame(animationFrame)
  animationFrame = null
  isPlaying.value = false
}

function togglePlay() {
  if (!trajectoryCoords.length) return
  if (isPlaying.value) { stopAnimation(); return }
  isPlaying.value = true
  if (currentStep >= trajectoryCoords.length - 1) currentStep = 0
  function animate() {
    if (!isPlaying.value) return
    currentStep++
    if (currentStep >= trajectoryCoords.length) {
      currentStep = trajectoryCoords.length - 1
      stopAnimation(); return
    }
    trajectoryMarker?.setLatLng(trajectoryCoords[currentStep]!)
    playProgress.value = Math.round((currentStep / (trajectoryCoords.length - 1)) * 100)
    animationFrame = requestAnimationFrame(() => setTimeout(animate, 120))
  }
  animate()
}

function onProgressChange(e: Event) {
  const val = parseInt((e.target as HTMLInputElement).value)
  currentStep = Math.round((val / 100) * (trajectoryCoords.length - 1))
  playProgress.value = val
  trajectoryMarker?.setLatLng(trajectoryCoords[currentStep]!)
}

async function classifyPOI() {
  if (!classifyInput.value.trim()) return
  const res = await axios.get('http://localhost:8000/api/classify', {
    params: { name: classifyInput.value }
  })
  classifyResult.value = res.data
}

onMounted(async () => {
  map = L.map(mapContainer.value!, { center: [39.9042, 116.4074], zoom: 11 })
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap'
  }).addTo(map)
  const [poisRes, catsRes] = await Promise.all([
    axios.get('http://localhost:8000/api/pois?limit=1368'),
    axios.get('http://localhost:8000/api/pois/categories')
  ])
  allFeatures = poisRes.data.features
  categories.value = catsRes.data
  renderFeatures(allFeatures)
})
</script>

<template>
  <div style="display:flex;width:100vw;height:100vh;font-family:sans-serif">
    <div style="width:210px;background:#1a1a2e;color:#eee;display:flex;flex-direction:column;padding:16px;gap:8px;overflow-y:auto;z-index:1000;flex-shrink:0">
      <div style="font-size:15px;font-weight:600;color:#fff;margin-bottom:4px">北京 POI 平台</div>

      <div v-if="selectedCount !== null"
        style="background:#2d4a2d;border-radius:6px;padding:8px;font-size:12px;color:#7ec87e;display:flex;justify-content:space-between;align-items:center">
        <span>框选到 {{ selectedCount }} 个</span>
        <span @click="clearSelection" style="cursor:pointer;color:#aaa">✕ 清除</span>
      </div>

      <button @click="toggleHeatmap" :style="{
        padding:'8px',borderRadius:'6px',border:'none',cursor:'pointer',fontSize:'13px',
        background: showHeatmap ? '#e74c3c' : '#2d2d44', color:'#fff'
      }">{{ showHeatmap ? '关闭热力图' : '开启热力图' }}</button>

      <button @click="toggleDraw" :style="{
        padding:'8px',borderRadius:'6px',border:'none',cursor:'pointer',fontSize:'13px',
        background: drawMode ? '#f39c12' : '#2d2d44', color:'#fff'
      }">{{ drawMode ? '绘制中...' : '框选过滤' }}</button>

      <button @click="toggleTrajectory" :style="{
        padding:'8px',borderRadius:'6px',border:'none',cursor:'pointer',fontSize:'13px',
        background: showTrajectory ? '#9b59b6' : '#2d2d44', color:'#fff'
      }">{{ showTrajectory ? '关闭轨迹' : '显示轨迹' }}</button>

      <div v-if="showTrajectory"
        style="background:#2d2d44;border-radius:8px;padding:10px;display:flex;flex-direction:column;gap:8px">
        <div style="font-size:12px;color:#aaa">轨迹回放</div>
        <button @click="togglePlay" :style="{
          padding:'7px',borderRadius:'6px',border:'none',cursor:'pointer',fontSize:'13px',
          background: isPlaying ? '#e74c3c' : '#27ae60', color:'#fff'
        }">{{ isPlaying ? '暂停' : (playProgress === 100 ? '重播' : '播放') }}</button>
        <input type="range" min="0" max="100" :value="playProgress"
          @input="onProgressChange"
          style="width:100%;cursor:pointer;accent-color:#f39c12"/>
        <div style="font-size:11px;color:#aaa;text-align:center">{{ playProgress }}%</div>
      </div>

      <div style="font-size:12px;color:#aaa;margin-top:4px">按分类筛选</div>

      <button @click="selectCategory('')" :style="{
        padding:'7px 10px',borderRadius:'6px',border:'none',cursor:'pointer',
        textAlign:'left',fontSize:'13px',color:'#fff',
        background: selectedCategory === '' ? '#4a4a6a' : '#2d2d44'
      }">全部 ({{ categories.reduce((s,c) => s+c.count, 0) }})</button>

      <button v-for="c in categories" :key="c.category"
        @click="selectCategory(c.category)" :style="{
          padding:'7px 10px',borderRadius:'6px',border:'none',cursor:'pointer',
          textAlign:'left',fontSize:'13px',color:'#fff',
          background: selectedCategory === c.category ? '#4a4a6a' : '#2d2d44',
          borderLeft: '3px solid ' + (categoryColors[c.category] ?? '#95a5a6')
        }">{{ c.category }} ({{ c.count }})</button>

        
      <div style="margin-top:8px;border-top:1px solid #2d2d44;padding-top:12px">
        <div style="font-size:12px;color:#aaa;margin-bottom:6px">自然语言搜索</div>
        <input v-model="searchQuery" placeholder="例：附近的医院..."
          @keyup.enter="naturalSearch"
          style="width:100%;padding:7px 8px;border-radius:6px;border:none;
                 background:#2d2d44;color:#fff;font-size:12px;box-sizing:border-box"/>
        <button @click="naturalSearch"
          :style="{
            width:'100%',marginTop:'6px',padding:'7px',borderRadius:'6px',
            border:'none',cursor:'pointer',fontSize:'13px',color:'#fff',
            background: isSearching ? '#888' : '#1D9E75'
          }">
          {{ isSearching ? '搜索中...' : '搜索地点' }}
        </button>
        <div v-if="searchResult"
          style="margin-top:8px;padding:8px;border-radius:6px;font-size:12px;
                 background:#2d2d44;color:#fff;display:flex;justify-content:space-between;align-items:center">
          <span>找到 {{ searchResult.total }} 个
            <b>{{ searchResult.detected_category ?? '相关' }}</b> POI</span>
          <span @click="clearSearch" style="cursor:pointer;color:#aaa">✕</span>
        </div>
      </div>
      <div style="margin-top:8px;border-top:1px solid #2d2d44;padding-top:12px">
        <div style="font-size:12px;color:#aaa;margin-bottom:6px">AI 分类测试</div>
        <input v-model="classifyInput" placeholder="输入 POI 名称..."
          @keyup.enter="classifyPOI"
          style="width:100%;padding:7px 8px;border-radius:6px;border:none;
                 background:#2d2d44;color:#fff;font-size:12px;box-sizing:border-box"/>
        <button @click="classifyPOI"
          style="width:100%;margin-top:6px;padding:7px;border-radius:6px;
                 border:none;cursor:pointer;background:#534AB7;color:#fff;font-size:13px">
          AI 识别分类
        </button>
        <div v-if="classifyResult"
          style="margin-top:8px;padding:8px;border-radius:6px;font-size:12px;background:#2d2d44;color:#fff">
          <div>分类：<b>{{ classifyResult.category }}</b></div>
          <div style="color:#aaa;margin-top:2px">置信度：{{ (classifyResult.confidence * 100).toFixed(1) }}%</div>
          <div style="margin-top:6px;background:#1a1a2e;border-radius:4px;overflow:hidden;height:6px">
            <div :style="{
              height:'100%',borderRadius:'4px',background:'#534AB7',
              width: (classifyResult.confidence * 100) + '%',
              transition:'width 0.3s'
            }"/>
          </div>
        </div>
      </div>
    </div>

    <div ref="mapContainer" style="flex:1" />
  </div>
</template>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
</style>