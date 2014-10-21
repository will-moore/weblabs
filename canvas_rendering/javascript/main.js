
$(document).ready(function(){
    var width = 512;
    var height = 512;
    var pixels;
    var canvas;
    var ctx;
    var svg;

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

        histogram(raw);
    };

    var histogram = function(pix) {

        // var hpix = ctx.getImageData(0, 0, width, height);

        var hdata = [],
            cdata;
        // go through 3 channels
        for (var c = 0; c < 3; c++){
            // go through all pixels of each channel (r,g,b or a)
            cdata = new Uint16Array(256);
            for (var i = c, n = pix.data.length; i < n; i+=4) {
                d = raw.data[i];
                cdata[d] = cdata[d] + 1;
            }
            hdata.push(cdata);
        }

        plotHistogram(hdata);

        // var maxVals = [d3.max(hdata[0]),
        //         d3.max(hdata[1]),
        //         d3.max(hdata[2])];
        // var yscale = d3.scale.linear()
        //     .domain([0, d3.max(maxVals)])
        //     .range([0, 300]);

        // d3.select(".chart")
        //   .selectAll("div")
        //     .data(hdata[0])
        //   .enter().append("div")
        //     .style("height", function(d) { return yscale(d) + "px"; })
        //     .style("left", function(d, i) { return (2 * i) + "px"; });

        // d3.select(".chart")
        //   .selectAll("div")
        //     .data(hdata[1])
        //   .enter().append("div")
        //     .style("height", function(d) { return yscale(d) + "px"; })
        //     .style("left", function(d, i) { return (2 * i) + "px"; })
        //     .style("background-color", "green");

        // d3.select(".chart")
        //   .selectAll("div")
        //     .data(hdata[2])
        //   .enter().append("div")
        //     .style("height", function(d) { return yscale(d) + "px"; })
        //     .style("left", function(d, i) { return (2 * i) + "px"; })
        //     .style("background-color", "blue");
    };

    var plotHistogram = function(h) {

        // This code adapted from http://jsfiddle.net/t8VUn/

        // data is list of 3 lists of 256 values

        // transform
        var data = [];
        for (var i=0; i<h[0].length; i++) {
            data.push({
                time: i+1,
                red: h[0][i],
                green: h[1][i],
                blue: h[2][i]
            });
        }

        var colours = {
            red: '#ff0000',
            green: '#00ff00',
            blue: '#0000ff'
        };
        

        // set up a colour variable
        var color = d3.scale.category10();

        // map one colour each to x, y and z
        // keys grabs the key value or heading of each key value pair in the json
        // but not time
        var keys = d3.keys(data[0]).filter(function(key) {
            return key !== "time";
        });
        color.domain(keys);

        // create a nested series for passing to the line generator
        var series = color.domain().map(function(name) {
            return {
                name: name,
                values: data.map(function(d) {
                    return {
                        time: d.time,
                        score: +d[name]
                    };
                })
            };
        });

        
        // Set the dimensions of the canvas / graph
        var margin = {
            top: 30,
            right: 0,
            bottom: 30,
            left: 0
        },
            width = 512 - margin.left - margin.right,
            height = 300 - margin.top - margin.bottom;

        // Set the ranges
        var x = d3.time.scale().range([0, width]);
        var y = d3.scale.linear().range([height, 0]);

        // Define the axes
        var xAxis = d3.svg.axis().scale(x)
            .orient("bottom").ticks(0);

        var yAxis = d3.svg.axis().scale(y)
            .orient("left").ticks(0);

        // Define the line
        // Note you plot the time / score pair from each key you created ealier 
        var valueline = d3.svg.line()
            .x(function(d) {
                return x(d.time);
            })
            .y(function(d) {
                return y(d.score);
            });


        // Adds the svg canvas
        svg = d3.select(".chart")
            .append("svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .append("g")
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

        // Scale the range of the data
        x.domain(d3.extent(data, function(d) {
            return d.time;
        }));
        
        // note the nested nature of this you need to dig an additional level
        y.domain([
            d3.min(series, function(c) {
                return d3.min(c.values, function(v) {
                    return v.score;
                });
            }),
            d3.max(series, function(c) {
                return d3.max(c.values, function(v) {
                    return v.score;
                });
            })
        ]);
        
        // create a variable called chart and bind the date
        // for each series append a g element and class it as series for css styling
        var chart = svg.selectAll(".series")
            .data(series)
            .enter().append("g")
            .attr("class", "series");

        // create the path for each series in the variable series i.e. x, y and z
        // pass each object called x, y nad z to the lne generator
        chart.append("path")
            .attr("class", "line")
            .attr("d", function(d) {
                return valueline(d.values);
            })
            .style("stroke", function(d) {
                return colours[d.name];
            });

        // Add the X Axis
        svg.append("g") // Add the X Axis
        .attr("class", "x axis")
            .attr("transform", "translate(0," + height + ")")
            .call(xAxis);

        // Add the Y Axis
        svg.append("g") // Add the Y Axis
        .attr("class", "y axis")
            .call(yAxis);


        // Add slider markers
        var line = svg.selectAll("rect")
        .data([0, 256]);

        var lineEnter = line.enter().append("rect");
        lineEnter.attr("y", 0);
        lineEnter.attr("height", 300);
        lineEnter.attr("width", 1);
        lineEnter.attr("x", function(d, i) { return d * 2; });

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
    // img.src = "data/" + "telophase.jpeg";
    img.src = "data/" + "prometaphase.jpeg";


    var chartRange = function(values, color) {
        // $("#start").css('left', 2 * values[0] + 'px');
        // $("#end").css('left', 2 * values[1] + 'px');
        var circle = svg.selectAll("rect")
        .data(values)
        .attr("x", function(d, i) { return d * 2; })
        .attr('fill', color);

        // var circleEnter = circle.enter().append("rect");
        // circleEnter.attr("y", 0);
        // circleEnter.attr("height", 300);
        // circleEnter.attr("width", 1);
        // circleEnter.attr("x", function(d, i) { return d * 2; });
    };


    // Set up sliders to render specified channel when they slide
    $("#slider_blue").slider({
        range: true,
        min: 0,
        max: 255,
        values: [0, 255],
        slide: function(event, ui) {
            render(2, ui.values[0], ui.values[1]);
            chartRange(ui.values, 'blue');
        }
    });

    $("#slider_green").slider({
        range: true,
        min: 0,
        max: 255,
        values: [0, 255],
        slide: function(event, ui) {
            render(1, ui.values[0], ui.values[1]);
            chartRange(ui.values, 'green');
        }
    });

    $("#slider_red").slider({
        range: true,
        min: 0,
        max: 255,
        values: [0, 255],
        slide: function(event, ui) {
            render(0, ui.values[0], ui.values[1]);
            chartRange(ui.values, 'red');
        }
    });
});