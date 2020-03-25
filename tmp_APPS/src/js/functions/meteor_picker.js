// Select a meteor (next/prev arrows)
function meteor_select(dir,all_frames_ids) {
   var next_id;
   var cur_id = parseInt($('#sel_frame_id').text());
   var cur_index = all_frames_ids.indexOf(cur_id); 

   if(dir=="prev") {
       if(cur_index==0) {
           next_id = all_frames_ids.length-1;
       } else {
           next_id = cur_index - 1;
       }
   } else {
       if(cur_index==all_frames_ids.length-1) {
           next_id = 0;
       } else {
           next_id = cur_index + 1;
       }
   }  

   // Open the next or previous one
   $('#reduc-tab table tbody tr#fr_' + all_frames_ids[next_id] + " a").click();

}



// Test if a frame is on the json and return the related data
function get_data_from_json(frame_id) {
   
   if(typeof json_data != 'undefined' && typeof json_data['frames'] != 'undefined') {

      for(var i=0; i< json_data['frames'].length; i++) {
         if(json_data['frames'][i]['fn']==frame_id) {
            return {'org_x': json_data['frames'][i]['x'], 'org_y':  json_data['frames'][i]['y']}
         }
      }
   }

   return false;
 
}