<template>
  <div class="patient-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">患者管理</h2>
        <p class="page-desc">查询患者档案，管理既往病史与联系信息</p>
      </div>
      <el-button type="primary" size="large" @click="openAdd" class="add-btn">
        <span class="btn-icon">＋</span> 新增患者
      </el-button>
    </div>

    <el-card class="search-card" shadow="never">
      <h3 class="search-title">患者查询</h3>
      <p class="search-hint">姓名支持模糊查询，患者编号和电话需完整输入；可结合性别、年龄缩小范围。</p>
      <el-form :model="filters" label-position="top" class="search-form" aria-label="患者查询" novalidate @submit.prevent="applySearch">
        <el-form-item label="患者检索" class="keyword-field">
          <el-input v-model="filters.keyword" placeholder="姓名 / 完整患者编号 / 完整电话" aria-label="患者检索" :prefix-icon="Search" clearable maxlength="50" />
        </el-form-item>
        <el-form-item label="性别">
          <el-select v-model="filters.gender" placeholder="全部性别" aria-label="筛选性别" clearable>
            <el-option v-for="gender in ['男', '女', '其他', '未知']" :key="gender" :label="gender" :value="gender" />
          </el-select>
        </el-form-item>
        <el-form-item label="年龄范围" class="age-field">
          <div class="age-range">
            <el-input v-model="filters.age_min" type="number" min="0" max="150" placeholder="最小年龄" aria-label="最小年龄" />
            <span>至</span>
            <el-input v-model="filters.age_max" type="number" min="0" max="150" placeholder="最大年龄" aria-label="最大年龄" />
          </div>
        </el-form-item>
        <div class="search-actions">
          <el-button type="primary" native-type="submit" :icon="Search" :loading="loading">查询</el-button>
          <el-button :icon="RefreshLeft" @click="resetSearch">重置</el-button>
        </div>
      </el-form>
      <el-alert v-if="searchError" class="search-validation" :title="searchError" type="warning" show-icon :closable="false" />
    </el-card>

    <el-card class="table-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="card-title">患者列表</span>
          <el-tag type="info" effect="plain" aria-live="polite">共 {{ total }} 位患者</el-tag>
        </div>
      </template>

      <el-alert v-if="loadError" :title="loadError" description="本次查询未完成，请重新加载；下方已有内容为上一次成功查询的结果。" type="error" :closable="false"><el-button link @click="load">重新加载</el-button></el-alert>
      <el-skeleton v-if="loading && !patients.length" :rows="6" animated />
      <el-table v-else
        v-loading="loading"
        row-key="id"
        :row-class-name="({ row }) => row.id === highlightedId ? 'recently-saved' : ''"
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
        <el-table-column prop="create_time" label="建档时间" min-width="170" />
        <el-table-column label="操作" width="156" align="center" fixed="right">
          <template #default="scope">
            <el-button type="primary" size="small" circle :icon="View" :aria-label="`查看${scope.row.name}的患者详情`" @click="showDetail(scope.row)" />
            <el-button type="primary" size="small" circle :icon="Edit" :loading="openingEdit === scope.row.id" :aria-label="`编辑${scope.row.name}`" @click="openEdit(scope.row)" />
            <el-button
              type="danger"
              size="small"
              circle
              @click="remove(scope.row)"
              :aria-label="`删除${scope.row.name}`"
              :loading="deleting === scope.row.id"
              class="del-btn"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty :description="hasFilters ? '未找到符合条件的患者，请调整查询条件' : '暂无患者档案，请先新增患者'" :image-size="70" />
        </template>
      </el-table>
      <div class="pagination-wrap">
        <span class="page-summary">第 {{ pagination.page }} 页 · 本页 {{ patients.length }} 位</span>
        <el-pagination
          :current-page="pagination.page"
          :page-size="pagination.page_size"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          :pager-count="5"
          :disabled="loading"
          layout="sizes, prev, pager, next"
          background
          @current-change="changePage"
          @size-change="changePageSize"
        />
      </div>
    </el-card>

    <el-dialog v-model="detailDialog" title="患者详情" width="620px" class="custom-dialog" @close="closeDetail">
      <el-skeleton v-if="detailLoading" :rows="7" animated />
      <el-alert v-else-if="detailError" :title="detailError" type="error" :closable="false">
        <el-button link @click="loadDetail">重新加载详情</el-button>
      </el-alert>
      <el-descriptions v-else-if="detail" :column="1" border class="patient-detail">
        <el-descriptions-item label="患者编号">{{ detail.patient_no || '未填写' }}</el-descriptions-item>
        <el-descriptions-item label="姓名">{{ detail.name || '未填写' }}</el-descriptions-item>
        <el-descriptions-item label="性别">{{ detail.gender || '未填写' }}</el-descriptions-item>
        <el-descriptions-item label="年龄">{{ detail.age === null ? '未填写' : `${detail.age} 岁` }}</el-descriptions-item>
        <el-descriptions-item label="电话">{{ detail.phone || '未填写' }}</el-descriptions-item>
        <el-descriptions-item label="地址">{{ detail.address || '未填写' }}</el-descriptions-item>
        <el-descriptions-item label="既往病史"><span class="history-text">{{ detail.medical_history || '未填写' }}</span></el-descriptions-item>
        <el-descriptions-item label="建档时间">{{ detail.create_time || '未填写' }}</el-descriptions-item>
      </el-descriptions>
      <template #footer><el-button @click="detailDialog = false">关闭</el-button></template>
    </el-dialog>

    <!-- 新增弹窗 -->
    <el-dialog
      v-model="dialog"
      :title="editingId ? '编辑患者' : '新增患者'"
      width="560px"
      :close-on-click-modal="false"
      :close-on-press-escape="!saving"
      :show-close="!saving"
      :before-close="done => { if (!saving) done() }"
      class="custom-dialog"
    >
      <el-alert v-if="saveError" :title="saveError" description="输入已保留，请重试保存。" type="error" show-icon :closable="false" class="save-error" />
      <el-form ref="formRef" :model="form" :rules="rules" :disabled="saving" label-width="80px" class="form" :class="{ 'validation-shake': shaking }">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="姓名" prop="name" required>
              <el-input v-model="form.name" placeholder="请输入姓名" maxlength="50" />
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
            <el-form-item label="年龄" prop="age">
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
        <el-button @click="dialog = false" :disabled="saving">取消</el-button>
        <el-button :type="saved ? 'success' : 'primary'" @click="save" :loading="saving && !saved" :disabled="saved" :icon="saved ? Check : undefined">{{ saved ? '已保存' : saving ? '保存中' : saveError ? '重试保存' : '保存' }}</el-button>
      </template>
    </el-dialog>
    <UndoNotice ref="undoRef" :restore="restorePatient" @restored="putRow" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Check, Search, RefreshLeft, View } from '@element-plus/icons-vue'
import { searchPatients, getPatientDetail, addPatient, deletePatient, updatePatient, restorePatient } from '../api/patient'
import UndoNotice from '../components/UndoNotice.vue'
import { useFeedback } from '../composables/useFeedback'

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
const openingEdit = ref(null)
const total = ref(0)
const pagination = reactive({ page: 1, page_size: 20 })
const emptyFilters = () => ({ keyword: '', gender: '', age_min: '', age_max: '' })
const filters = reactive(emptyFilters())
const activeFilters = ref({})
const hasFilters = computed(() => Object.keys(activeFilters.value).length > 0)
const searchError = ref('')
const detailDialog = ref(false)
const detailLoading = ref(false)
const detail = ref(null)
const detailError = ref('')
let selectedPatientId, listRequest = 0, detailRequest = 0, disposed = false
const rules = {
  name: [{ required: true, whitespace: true, message: '请输入患者姓名', trigger: 'blur' }],
  age: [{ validator: (_, value, done) => value === '' || value === null || (/^\d+$/.test(String(value)) && Number(value) <= 150) ? done() : done(new Error('年龄应为 0～150 的整数')), trigger: 'blur' }]
}

const form = reactive({
  patient_no: '',
  name: '',
  gender: '',
  age: '',
  phone: '',
  address: '',
  medical_history: ''
})

async function load() {
  const current = ++listRequest
  loading.value = true
  loadError.value = ''
  try {
    const { data } = await searchPatients({ ...activeFilters.value, ...pagination })
    if (current !== listRequest) return
    if (!data.items.length && pagination.page > Math.max(1, data.pages)) {
      pagination.page = Math.max(1, data.pages)
      return await load()
    }
    patients.value = data.items
    total.value = data.total
  } catch (error) { if (current === listRequest) loadError.value = error.message }
  finally { if (current === listRequest) loading.value = false }
}

function applySearch() {
  const values = Object.fromEntries(Object.entries(filters).map(([key, value]) => [key, String(value ?? '').trim()]))
  for (const key of ['age_min', 'age_max']) {
    if (values[key] && (!/^\d+$/.test(values[key]) || Number(values[key]) > 150)) {
      searchError.value = '年龄应为 0～150 的整数'
      return
    }
  }
  if (values.age_min && values.age_max && Number(values.age_min) > Number(values.age_max)) {
    searchError.value = '最小年龄不能大于最大年龄'
    return
  }
  searchError.value = ''
  activeFilters.value = Object.fromEntries(Object.entries(values).filter(([, value]) => value !== ''))
  pagination.page = 1
  load()
}

function resetSearch() {
  Object.assign(filters, emptyFilters())
  activeFilters.value = {}
  searchError.value = ''
  pagination.page = 1
  load()
}

function changePage(page) {
  if (page === pagination.page) return
  pagination.page = page
  load()
}

function changePageSize(size) {
  pagination.page_size = size
  pagination.page = 1
  load()
}

function showDetail(row) {
  selectedPatientId = row.id
  detailDialog.value = true
  loadDetail()
}

async function loadDetail() {
  const current = ++detailRequest
  detailLoading.value = true
  detail.value = null
  detailError.value = ''
  try {
    const response = await getPatientDetail(selectedPatientId)
    if (current === detailRequest) detail.value = response.data
  } catch (error) { if (current === detailRequest) detailError.value = error.message }
  finally { if (current === detailRequest) detailLoading.value = false }
}

function closeDetail() {
  detailRequest++
  detail.value = null
}

onMounted(load)
onBeforeUnmount(() => { disposed = true; listRequest++; detailRequest++ })

function openAdd() {
  editingId.value = null
  saved.value = false
  saveError.value = ''
  Object.assign(form, { patient_no: '', name: '', gender: '', age: '', phone: '', address: '', medical_history: '' })
  dialog.value = true
  nextTick(() => formRef.value?.clearValidate())
}

async function openEdit(row) {
  if (openingEdit.value !== null) return
  openingEdit.value = row.id
  try {
    const { data } = await getPatientDetail(row.id)
    if (disposed) return
    openAdd()
    editingId.value = row.id
    for (const key of Object.keys(form)) form[key] = data[key] ?? ''
  } catch { /* 请求失败由拦截器提示，未获得完整档案时不打开编辑表单。 */ }
  finally { openingEdit.value = null }
}

async function putRow(row) {
  await load()
  highlight(row.id)
}

async function save() {
  if (saving.value) return
  saveError.value = ''
  saving.value = true
  if (!await validate(formRef.value)) { saving.value = false; return }
  try {
    const response = await (editingId.value ? updatePatient(editingId.value, form) : addPatient(form))
    saved.value = true
    await new Promise(resolve => setTimeout(resolve, 700))
    dialog.value = false
    if (!editingId.value) pagination.page = 1
    await putRow(response.data)
    ElMessage.success(editingId.value ? '患者信息已更新' : '新增成功')
  } catch (error) { saveError.value = error.message }
  finally { saving.value = false; saved.value = false }
}

async function remove(row) {
  if (deleting.value !== null) return
  deleting.value = row.id
  try {
    await ElMessageBox.confirm(`即将删除患者「${row.name}」（${row.patient_no}）。此操作会移除患者档案；有关联病历时禁止删除。删除后 30 秒内可撤销。`, '确认删除患者', { type: 'error', customClass: 'danger-confirm', confirmButtonText: '确定', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' })
    const response = await deletePatient(row.id)
    patients.value = patients.value.filter(item => item.id !== row.id)
    total.value = Math.max(0, total.value - 1)
    undoRef.value.show(`患者「${row.name}」`, response.data)
    await load()
  } catch {
    // 取消删除不提示错误；请求失败由拦截器提示。
  }
  finally { deleting.value = null }
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

.search-card { border-radius: 16px; border-color: #e2e8f0; }
.search-title { margin: 0 0 6px; font-size: 16px; color: #2d3748; }
.search-hint { margin: 0 0 18px; color: #718096; font-size: 13px; line-height: 1.6; }
.search-form { display: grid; grid-template-columns: minmax(220px, 2fr) minmax(110px, 1fr) minmax(210px, 1.4fr) auto; gap: 16px; align-items: end; }
.search-form :deep(.el-form-item) { margin-bottom: 0; min-width: 0; }
.search-form :deep(.el-select) { width: 100%; }
.age-range, .search-actions { display: flex; align-items: center; gap: 8px; }
.age-range { width: 100%; color: #718096; }
.age-range :deep(.el-input) { min-width: 0; }
.search-actions { min-height: 32px; }
.search-actions :deep(.el-button + .el-button) { margin-left: 0; }
.search-validation { margin-top: 16px; }
.pagination-wrap { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; padding-top: 20px; }
.page-summary { font-size: 13px; color: #718096; }
.patient-detail :deep(.el-descriptions__label) { width: 90px; white-space: nowrap; }
.patient-detail :deep(.el-descriptions__content) { overflow-wrap: anywhere; }
.history-text { white-space: pre-wrap; }
@media (max-width: 1200px) {
  .search-form { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
}
@media (max-width: 600px) {
  .search-form { grid-template-columns: minmax(0, 1fr); }
  .search-actions :deep(.el-button) { flex: 1; }
  .pagination-wrap :deep(.el-pagination) { flex-wrap: wrap; row-gap: 10px; max-width: 100%; }
  .pagination-wrap :deep(.el-pagination__sizes) { margin-right: 4px; }
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
