
$(document).ready(function(){
    var width = 512;
    var height = 512;
    var pixels;
    var canvas;
    var ctx;

    $("#canvas").css({'width': width/+'px', 'height': height/+'px'});

    var img = new Image();

    // When we have the Image data, use it to populate the canvas
    img.onload = function() {
        canvas = document.getElementById("canvas");
        canvas.width = width;
        canvas.height = height;

        ctx = canvas.getContext("2d");
        ctx.drawImage(img, 0, 0);

        // and save a copy of the data
        raw = ctx.getImageData(0, 0, width, height);
    };

    // Update the specified channel of the image
    var render = function(channel, start, end) {

        // get the current pixel data...
        pixels = ctx.getImageData(0, 0, width, height);

        var d;
        // go through all pixels of the specified channel (r,g,b or a)
        for (var i = channel, n = pixels.data.length; i < n; i+=4) {
            d = raw.data[i];
            if (d < start) {
                d = 0;
            } else if (d > end) {
                d = 255;
            } else {
                d = ((d - start) / (end - start)) * 255;
            }
            pixels.data[i] = d;
        }

        ctx.putImageData(pixels, 0, 0);
    };

    // Kick off the loading of image
    img.src = "data/" + "cell.jpeg";


    // Set up sliders to render specified channel when they slide
    $("#slider_blue").slider({
        range: true,
        min: 0,
        max: 255,
        values: [0, 255],
        slide: function(event, ui) {
            render(2, ui.values[0], ui.values[1]);
        }
    });

    $("#slider_green").slider({
        range: true,
        min: 0,
        max: 255,
        values: [0, 255],
        slide: function(event, ui) {
            render(1, ui.values[0], ui.values[1]);
        }
    });

    $("#slider_red").slider({
        range: true,
        min: 0,
        max: 255,
        values: [0, 255],
        slide: function(event, ui) {
            render(0, ui.values[0], ui.values[1]);
        }
    });
});