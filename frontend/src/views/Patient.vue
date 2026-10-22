<template>
  <div class="patient-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">患者管理</h2>
        <p class="page-desc">管理医院患者信息，支持新增、删除操作</p>
      </div>
      <el-button type="primary" size="large" @click="openAdd" class="add-btn">
        <span class="btn-icon">＋</span> 新增患者
      </el-button>
    </div>

    <el-card class="table-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="card-title">患者列表</span>
          <el-tag type="info" effect="plain">{{ patients.length }} 条记录</el-tag>
        </div>
      </template>

      <el-table
        :data="patients"
        style="width: 100%"
        stripe
        :header-cell-style="{ background: '#f7fafc', color: '#4a5568', fontWeight: '600' }"
      >
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column prop="patient_no" label="患者编号" width="140" />
        <el-table-column prop="name" label="姓名" width="120">
          <template #default="{ row }">
            <div class="name-cell">
              <span class="name-avatar">{{ row.name?.charAt(0) || '?' }}</span>
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="gender" label="性别" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.gender === '男' ? 'primary' : 'danger'" size="small" round>
              {{ row.gender || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="age" label="年龄" width="80" align="center" />
        <el-table-column prop="phone" label="电话" width="140" />
        <el-table-column prop="address" label="地址" min-width="160" show-overflow-tooltip />
        <el-table-column label="操作" width="100" align="center">
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
      title="新增患者"
      width="560px"
      :close-on-click-modal="false"
      class="custom-dialog"
    >
      <el-form :model="form" label-width="80px" class="form">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="姓名" required>
              <el-input v-model="form.name" placeholder="请输入姓名" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="患者编号">
              <el-input v-model="form.patient_no" placeholder="自动生成" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="性别">
              <el-select v-model="form.gender" placeholder="请选择" style="width:100%">
                <el-option label="男" value="男" />
                <el-option label="女" value="女" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="年龄">
              <el-input v-model="form.age" type="number" placeholder="请输入年龄" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="电话">
              <el-input v-model="form.phone" placeholder="请输入电话" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="地址">
              <el-input v-model="form.address" placeholder="请输入地址" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="既往病史">
          <el-input v-model="form.medical_history" type="textarea" :rows="3" placeholder="请输入既往病史" />
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
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete } from '@element-plus/icons-vue'
import { getPatients, addPatient, deletePatient } from '../api/patient'

const patients = ref([])
const dialog = ref(false)
const saving = ref(false)

const form = reactive({
  patient_no: '',
  name: '',
  gender: '',
  age: '',
  phone: '',
  address: '',
  medical_history: ''
})

function load() {
  getPatients()
    .then(res => { patients.value = res.data })
    .catch(() => {})
}

onMounted(load)

function openAdd() {
  Object.assign(form, { patient_no: '', name: '', gender: '', age: '', phone: '', address: '', medical_history: '' })
  dialog.value = true
}

function save() {
  if (saving.value) return
  if (!form.name.trim()) { ElMessage.warning('姓名不能为空'); return }
  saving.value = true
  addPatient(form)
    .then(() => {
      ElMessage.success('新增成功')
      dialog.value = false
      load()
    })
    .catch(() => {})
    .finally(() => { saving.value = false })
}

async function remove(id) {
  try {
    await ElMessageBox.confirm('确定要删除该患者吗？有关联病历的患者需要先处理病历。', '提示', { type: 'warning' })
    await deletePatient(id)
    ElMessage.success('删除成功')
    load()
  } catch {
    // 取消删除不提示错误；请求失败由拦截器提示。
  }
}
</script>

<style scoped>
.patient-page {
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

.name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.name-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
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
