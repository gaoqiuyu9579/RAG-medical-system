<template>
  <div class="medical-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">电子病历管理</h2>
        <p class="page-desc">记录和管理患者病历信息，支持病历录入</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" plain size="large" :icon="Search" @click="$router.push('/patient')">查询患者</el-button>
        <el-button type="primary" size="large" @click="openAdd" class="add-btn">
          <span class="btn-icon">＋</span> 新增病历
        </el-button>
      </div>
    </div>

    <el-alert
      v-if="unlinkedCount"
      :title="`有 ${unlinkedCount} 条历史病历的患者信息缺失，待核对`"
      description="这些病历已保留。请先核实原患者信息，再修正关联；不要将病历随意归到其他患者名下。"
      type="warning"
      show-icon
      :closable="false"
    />

    <el-card class="table-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="card-title">病历列表</span>
          <el-tag type="info" effect="plain">{{ records.length }} 条记录</el-tag>
        </div>
      </template>

      <el-alert v-if="loadError" :title="loadError" type="error" :closable="false"><el-button link @click="load">重新加载</el-button></el-alert>
      <el-skeleton v-if="loading && !records.length" :rows="6" animated />
      <el-table v-else
        v-loading="loading"
        row-key="id"
        :row-class-name="({ row }) => row.id === highlightedId ? 'recently-saved' : ''"
        :data="records"
        style="width: 100%"
        stripe
        :header-cell-style="{ background: '#f7fafc', color: '#4a5568', fontWeight: '600' }"
      >
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column label="患者姓名" width="120">
          <template #default="{ row }">
            {{ getPatientName(row.patient_id) }}
          </template>
        </el-table-column>
        <el-table-column prop="doctor_name" label="医生" width="120">
          <template #default="{ row }">
            <div class="doctor-cell">
              <span class="doctor-avatar">{{ row.doctor_name?.charAt(0) || 'D' }}</span>
              <span>{{ row.doctor_name || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="diagnosis" label="诊断" min-width="180" show-overflow-tooltip />
        <el-table-column prop="symptom" label="症状" min-width="180" show-overflow-tooltip />
        <el-table-column prop="treatment" label="治疗方案" min-width="180" show-overflow-tooltip />
        <el-table-column prop="medicine" label="用药" min-width="150" show-overflow-tooltip />
        <el-table-column prop="record_time" label="记录时间" width="170" align="center">
          <template #default="{ row }">
            <span class="time-text">{{ formatTime(row.record_time) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="124" align="center" fixed="right">
          <template #default="scope">
            <el-button type="primary" size="small" circle :icon="Edit" :aria-label="`编辑${getPatientName(scope.row.patient_id)}的病历`" @click="openEdit(scope.row)" />
            <el-button
              type="danger"
              size="small"
              circle
              @click="remove(scope.row)"
              :aria-label="`删除${getPatientName(scope.row.patient_id)}的病历`"
              :loading="deleting === scope.row.id"
              class="del-btn"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增弹窗 -->
    <el-dialog
      v-model="dialog"
      :title="editingId ? '编辑病历' : '录入病历'"
      width="620px"
      :close-on-click-modal="false"
      :close-on-press-escape="!saving"
      :show-close="!saving"
      :before-close="done => { if (!saving) done() }"
      class="custom-dialog"
    >
      <el-alert v-if="saveError" :title="saveError" description="输入已保留，请重试保存。" type="error" show-icon :closable="false" class="save-error" />
      <el-form ref="formRef" :model="form" :rules="rules" :disabled="saving" label-width="90px" class="form" :class="{ 'validation-shake': shaking }">
        <el-form-item label="选择患者" prop="patient_id" required>
          <el-select v-model="form.patient_id" placeholder="请选择患者" style="width:100%" filterable>
            <el-option
              v-for="p in patients"
              :key="p.id"
              :label="p.name + ' (ID:' + p.id + ')'"
              :value="p.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="医生">
          <el-input v-model="form.doctor_name" placeholder="请输入医生姓名" />
        </el-form-item>
        <el-form-item label="诊断">
          <el-input v-model="form.diagnosis" placeholder="请输入诊断结果" />
        </el-form-item>
        <el-form-item label="症状">
          <el-input v-model="form.symptom" type="textarea" :rows="2" placeholder="请输入症状描述" />
        </el-form-item>
        <el-form-item label="治疗方案">
          <el-input v-model="form.treatment" type="textarea" :rows="2" placeholder="请输入治疗方案" />
        </el-form-item>
        <el-form-item label="用药">
          <el-input v-model="form.medicine" type="textarea" :rows="2" placeholder="请输入用药信息" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialog = false" :disabled="saving">取消</el-button>
        <el-button :type="saved ? 'success' : 'primary'" @click="save" :loading="saving && !saved" :disabled="saved" :icon="saved ? Check : undefined">{{ saved ? '已保存' : saving ? '保存中' : saveError ? '重试保存' : '保存' }}</el-button>
      </template>
    </el-dialog>
    <UndoNotice ref="undoRef" :restore="restoreRecord" @restored="putRow" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Check, Search } from '@element-plus/icons-vue'
import { getRecords, addRecord, deleteRecord, updateRecord, restoreRecord } from '../api/medical'
import UndoNotice from '../components/UndoNotice.vue'
import { useFeedback } from '../composables/useFeedback'
import { getPatients } from '../api/patient'

const records = ref([])
const patients = ref([])
const dialog = ref(false)
const { saving, saved, shaking, highlightedId, highlight, validate } = useFeedback()
const formRef = ref(null)
const undoRef = ref(null)
const editingId = ref(null)
const loading = ref(true)
const loadError = ref('')
const saveError = ref('')
const deleting = ref(null)
const rules = { patient_id: [{ required: true, message: '请选择关联患者', trigger: 'change' }] }
const dataLoaded = ref(false)
const unlinkedCount = computed(() => dataLoaded.value
  ? records.value.filter(record => !patients.value.some(patient => patient.id === record.patient_id)).length
  : 0)

const form = reactive({
  patient_id: null,
  doctor_name: '',
  diagnosis: '',
  symptom: '',
  treatment: '',
  medicine: ''
})

function getPatientName(patientId) {
  const p = patients.value.find(x => x.id === patientId)
  return p ? p.name : (`待核对（ID:${patientId}）`)
}

async function load() {
  loading.value = true
  try {
      const [recordResponse, patientResponse] = await Promise.all([getRecords(), getPatients()])
      records.value = recordResponse.data
      patients.value = patientResponse.data
      dataLoaded.value = true
      loadError.value = ''
  } catch (error) { loadError.value = error.message }
  finally { loading.value = false }
}

onMounted(load)

function openAdd() {
  editingId.value = null
  saved.value = false
  saveError.value = ''
  Object.assign(form, { patient_id: null, doctor_name: '', diagnosis: '', symptom: '', treatment: '', medicine: '' })
  dialog.value = true
  nextTick(() => formRef.value?.clearValidate())
}

function openEdit(row) {
  openAdd()
  editingId.value = row.id
  for (const key of Object.keys(form)) form[key] = row[key] ?? ''
}

function putRow(row) {
  const index = records.value.findIndex(item => item.id === row.id)
  if (index < 0) records.value.unshift(row)
  else records.value.splice(index, 1, row)
  highlight(row.id)
}

async function save() {
  if (saving.value) return
  saveError.value = ''
  saving.value = true
  if (!await validate(formRef.value)) { saving.value = false; return }
  try {
    const response = await (editingId.value ? updateRecord(editingId.value, form) : addRecord(form))
    saved.value = true
    await new Promise(resolve => setTimeout(resolve, 700))
    dialog.value = false
    putRow(response.data)
    ElMessage.success('保存成功')
  } catch (error) { saveError.value = error.message }
  finally { saving.value = false; saved.value = false }
}

function formatTime(time) {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  })
}

async function remove(row) {
  if (deleting.value !== null) return
  deleting.value = row.id
  try {
    await ElMessageBox.confirm(`即将删除患者「${getPatientName(row.patient_id)}」的病历（ID:${row.id}，诊断：${row.diagnosis || '未填写'}）。此操作会移除该诊疗记录，删除后 30 秒内可撤销。`, '确认删除病历', { type: 'error', customClass: 'danger-confirm', confirmButtonText: '确定', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' })
    const response = await deleteRecord(row.id)
    records.value = records.value.filter(item => item.id !== row.id)
    undoRef.value.show(`「${getPatientName(row.patient_id)}」的病历`, response.data)
  } catch {
    // 取消删除不提示错误；请求失败由拦截器提示。
  }
  finally { deleting.value = null }
}
</script>

<style scoped>
.header-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.header-actions :deep(.el-button + .el-button) { margin-left: 0; }
.medical-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #1a202c;
  margin: 0 0 4px;
}

.page-desc {
  font-size: 13px;
  color: #718096;
  margin: 0;
}

.add-btn {
  padding: 10px 24px;
  border-radius: 10px;
  font-weight: 600;
}

.btn-icon {
  font-size: 18px;
  margin-right: 4px;
}

.table-card {
  border-radius: 16px;
  border: 1px solid #e2e8f0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #2d3748;
}

.doctor-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.doctor-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #38a169, #68d391);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.time-text {
  font-size: 12px;
  color: #718096;
}

.del-btn {
  background: #fff5f5;
  border-color: #fed7d7;
  color: #e53e3e;
}

.del-btn:hover {
  background: #fed7d7;
}

.form {
  padding: 4px 0;
}

:deep(.el-dialog) {
  border-radius: 16px !important;
  overflow: hidden;
}

:deep(.el-dialog__header) {
  background: linear-gradient(135deg, #2b6cb0, #3182ce);
  padding: 20px 24px;
  margin-right: 0;
}

:deep(.el-dialog__header .el-dialog__title) {
  color: #fff;
  font-weight: 600;
}

:deep(.el-dialog__header .el-dialog__headerbtn .el-dialog__close) {
  color: #fff;
}

:deep(.el-dialog__body) {
  padding: 24px;
}

:deep(.el-dialog__footer) {
  padding: 16px 24px;
  border-top: 1px solid #edf2f7;
}
</style>
