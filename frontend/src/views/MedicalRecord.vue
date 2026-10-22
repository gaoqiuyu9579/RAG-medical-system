<template>
  <div class="medical-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">电子病历管理</h2>
        <p class="page-desc">记录和管理患者病历信息，支持病历录入</p>
      </div>
      <el-button type="primary" size="large" @click="openAdd" class="add-btn">
        <span class="btn-icon">＋</span> 新增病历
      </el-button>
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

      <el-table
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
        <el-table-column label="操作" width="80" align="center">
          <template #default="scope">
            <el-button
              type="danger"
              size="small"
              circle
              @click="remove(scope.row.id)"
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
      title="录入病历"
      width="620px"
      :close-on-click-modal="false"
      class="custom-dialog"
    >
      <el-form :model="form" label-width="90px" class="form">
        <el-form-item label="选择患者" required>
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
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="save" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import { getRecords, addRecord, deleteRecord } from '../api/medical'
import { getPatients } from '../api/patient'

const records = ref([])
const patients = ref([])
const dialog = ref(false)
const saving = ref(false)
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

function load() {
  Promise.all([getRecords(), getPatients()])
    .then(([recordResponse, patientResponse]) => {
      records.value = recordResponse.data
      patients.value = patientResponse.data
      dataLoaded.value = true
    })
    .catch(() => {})
}

onMounted(load)

function openAdd() {
  Object.assign(form, { patient_id: null, doctor_name: '', diagnosis: '', symptom: '', treatment: '', medicine: '' })
  dialog.value = true
}

function save() {
  if (saving.value) return
  if (!form.patient_id) { ElMessage.warning('请选择患者'); return }
  saving.value = true
  addRecord(form)
    .then(() => {
      ElMessage.success('保存成功')
      dialog.value = false
      load()
    })
    .catch(() => {})
    .finally(() => { saving.value = false })
}

function formatTime(time) {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  })
}

async function remove(id) {
  try {
    await ElMessageBox.confirm('确定要删除该病历吗？', '提示', { type: 'warning' })
    await deleteRecord(id)
    ElMessage.success('删除成功')
    load()
  } catch {
    // 取消删除不提示错误；请求失败由拦截器提示。
  }
}
</script>

<style scoped>
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
