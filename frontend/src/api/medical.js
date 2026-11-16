import request from "./request"

export const updateRecord = (id, data) => request.put(`/medical/update/${id}`, data)
export const restoreRecord = token => request.post('/medical/restore', { token })



export function getRecords(){
    return request.get("/medical/list")
}



export function addRecord(data){
    return request.post("/medical/add", data)
}


export function deleteRecord(id){
    return request.delete(`/medical/delete/${id}`)
}
