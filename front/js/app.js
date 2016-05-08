app=angular.module('app', []);

app.controller('main', function($scope,$http) {
	$scope.list=[];
	$scope.book="";
	$scope.extension="";

	$scope.getList = function() {
		$http.get("/test/").then(
		function(data) {
			$scope.list=data.data;
		},
		function(data){
			console.log("error");
			console.log(data);
		});
	}
	$scope.getList();

	$scope.download = function(book) {
		$http.post("/test/?adasasd",{"type":"BOOK","book":book}).then(
		function(data) {
			$scope.getList();
		},
		function(data){
			console.log("error");
			console.log(data);
		});
	};
	$scope.searchbook = function(book,extension){
		$http.post("/test/?ewqewqewq", {"type":"search","book":book,"extension":extension}).then(
		function(data) {
			console.log("success");
			$scope.getlist();
		},
		function(data){
			console.log("err");
		});
	};
});
