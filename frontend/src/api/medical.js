import request from "./request"



export function getRecords(){
    return request.get("/medical/list")
}



export function addRecord(data){
    return request.post("/medical/add", data)
}


export function deleteRecord(id){
    return request.delete(`/medical/delete/${id}`)
}
