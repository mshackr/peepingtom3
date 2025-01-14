var page = require('webpage').create();
var system = require('system');

if (system.args.length !== 3) {
    console.log('Usage: phantomjs screenshot.js <URL> <output_file>');
    phantom.exit(1);
}

var url = system.args[1];
var output = system.args[2];

page.viewportSize = { width: 800, height: 600 };
page.clipRect = { top: 0, left: 0, width: 800, height: 600 };

page.open(url, function (status) {
    if (status !== 'success') {
        console.log('Unable to load the URL!');
        phantom.exit(1);
    } else {
        window.setTimeout(function () {
            page.render(output);
            console.log('Screenshot saved to ' + output);
            phantom.exit();
        }, 200); // Wait for 2 seconds to ensure page loads completely
    }
});