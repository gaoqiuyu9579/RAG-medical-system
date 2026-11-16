<template>
  <div class="statistics-page">
    <div class="page-header"><div><h2>数据统计分析</h2><p>基于当前患者档案与病历记录实时汇总</p></div><el-button :loading="loading" @click="load">刷新数据</el-button></div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <el-skeleton v-if="loading && !data" :rows="12" animated />
    <template v-else-if="data">
      <div class="analytics-stats">
        <div v-for="card in cards" :key="card.key" class="analytics-card"><span>{{ card.label }}</span><strong><CountUp :value="data[card.key]" /><small>{{ card.unit }}</small></strong></div>
      </div>
      <div class="chart-grid" v-loading="loading">
        <el-card shadow="hover"><template #header><h3>患者年龄分布</h3><p>统计全部已登记患者，未填年龄单独归类</p></template><div ref="ageRef" class="chart" role="img" :aria-label="`患者年龄分布：${data.ageDistribution.map(item => item.name + item.value + '人').join('，')}`"></div><el-empty v-if="!data.patientCount" description="暂无患者档案，请先登记患者" :image-size="60" /></el-card>
        <el-card shadow="hover"><template #header><div class="trend-heading"><h3>病历录入趋势</h3><el-select v-model="days" aria-label="统计时间范围" style="width: 125px" :disabled="loading" @change="load"><el-option v-for="value in [7,30,90]" :key="value" :label="`近 ${value} 天`" :value="value" /></el-select></div><p>按病历记录日期统计，包含零记录日期</p></template><div ref="trendRef" class="chart" role="img" :aria-label="`近${days}天录入病历${data.periodRecords}份`"></div><el-empty v-if="!data.periodRecords" description="所选时段暂无病历" :image-size="60" /></el-card>
      </div>
      <p class="data-note">统计口径：年龄分布按患者人数；趋势按病历份数。同一患者多次就诊分别计入。</p>
    </template>
  </div>
</template>
<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, AriaComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import request from '../api/request'
import CountUp from '../components/CountUp.vue'
echarts.use([BarChart, LineChart, GridComponent, TooltipComponent, AriaComponent, CanvasRenderer])
const days = ref(30), loading = ref(true), data = ref(null), error = ref('')
const ageRef = ref(null), trendRef = ref(null)
const cards = [{ key: 'patientCount', label: '登记患者', unit: '人' }, { key: 'recordCount', label: '病历总数', unit: '份' }, { key: 'periodRecords', label: '所选时段病历', unit: '份' }, { key: 'averageAge', label: '平均年龄（已填写）', unit: '岁' }]
let ageChart, trendChart, observer, disposed = false
function draw() {
  if (disposed || !ageRef.value || !trendRef.value) return
  ageChart ??= echarts.init(ageRef.value)
  trendChart ??= echarts.init(trendRef.value)
  const base = { animationDuration: matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 800, tooltip: { trigger: 'axis', renderMode: 'richText', confine: true }, grid: { top: 25, left: 42, right: 16, bottom: 55 }, yAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { color: '#edf2f7' } } } }
  ageChart.setOption({ ...base, color: ['#5385d8'], xAxis: { type: 'category', data: data.value.ageDistribution.map(item => item.name), axisLabel: { interval: 0, rotate: 24, fontSize: 10 } }, series: [{ type: 'bar', name: '患者人数', barMaxWidth: 38, data: data.value.ageDistribution.map(item => item.value), itemStyle: { borderRadius: [6, 6, 0, 0] }, label: { show: true, position: 'top', color: '#4b6883' } }] })
  trendChart.setOption({ ...base, color: ['#26a69a'], xAxis: { type: 'category', boundaryGap: false, data: data.value.trend.map(item => item.date.slice(5)) }, series: [{ type: 'line', name: '病历份数', smooth: true, symbolSize: 6, areaStyle: { color: '#26a69a', opacity: .1 }, data: data.value.trend.map(item => item.value) }] })
  if (!observer) {
    observer = new ResizeObserver(() => { ageChart?.resize(); trendChart?.resize() })
    observer.observe(ageRef.value); observer.observe(trendRef.value)
  }
}
async function load() {
  loading.value = true
  try {
    const response = await request.get('/user/analytics', { params: { days: days.value } })
    data.value = response.data; error.value = ''
    await nextTick(); draw()
  } catch (failure) { error.value = failure.message }
  finally { loading.value = false }
}
onMounted(load)
onBeforeUnmount(() => { disposed = true; observer?.disconnect(); ageChart?.dispose(); trendChart?.dispose() })
</script>
<style scoped>
.statistics-page { display: grid; gap: 22px; }.page-header, .trend-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }h2 { margin: 0 0 6px; font-size: 22px; color: #1e293b; }p { margin: 0; font-size: 13px; color: #7b8b9f; }h3 { margin: 0 0 6px; font-size: 16px; color: #334155; }.analytics-stats { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 18px; }.analytics-card { background: white; padding: 22px; border: 1px solid #e6edf4; border-radius: 14px; transition: transform .25s, box-shadow .25s; }.analytics-card:hover { transform: translateY(-3px); box-shadow: 0 12px 28px #1e3d5c15; }.analytics-card > span { display: block; color: #718096; font-size: 13px; }.analytics-card strong { display: block; margin-top: 14px; font-size: 32px; color: #24466b; }.analytics-card small { font-size: 13px; color: #8493a6; margin-left: 8px; font-weight: normal; }.chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; min-width: 0; }.chart-grid :deep(.el-card) { min-width: 0; border-radius: 14px; }.chart { width: 100%; height: 320px; }.data-note { font-size: 12px; }
@media(max-width: 1100px) { .chart-grid { grid-template-columns: 1fr; } }@media(max-width: 768px) { .analytics-stats { grid-template-columns: 1fr 1fr; gap: 12px; }.analytics-card { padding: 16px; }.chart { height: 280px; } }
</style>
