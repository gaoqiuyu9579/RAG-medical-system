import request from "./request"



export function getPatients(){
    return request.get("/patient/list")
}



export function addPatient(data){
    return request.post("/patient/add", data)
}



export function deletePatient(id){
    return request.delete(`/patient/delete/${id}`)
}
