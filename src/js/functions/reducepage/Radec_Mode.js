var RADEC_MODE = false; // Shared with canvas-interactions



// Remove All stars info from canvas
function remove_stars_info_from_canvas() {
   var objects = canvas.getObjects()
   $.each(objects,function(i,v){
       if(v.type=='star_info') {
           canvas.remove(objects[i]);
       }
   });
}


$('#radec_mode').click(function() {
   RADEC_MODE != RADEC_MODE;
   
   console.log("RADEC_MODE ", RADEC_MODE );

   if(RADEC_MODE) {
      // We hide the stars
      remove_stars_info_from_canvas();
   }
})