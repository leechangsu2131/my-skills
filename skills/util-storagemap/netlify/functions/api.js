const app = require('../../server');
const serverless = require('serverless-http');

module.exports.handler = serverless(app);
