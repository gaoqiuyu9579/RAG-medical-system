import request from "./request"

export const updatePatient = (id, data) => request.put(`/patient/update/${id}`, data)
export const restorePatient = token => request.post('/patient/restore', { token })
export const searchPatients = params => request.get('/patient/search', { params })
export const getPatientDetail = id => request.get(`/patient/detail/${id}`)



export function getPatients(){
    return request.get("/patient/list")
}



export function addPatient(data){
    return request.post("/patient/add", data)
}



export function deletePatient(id){
    return request.delete(`/patient/delete/${id}`)
}
