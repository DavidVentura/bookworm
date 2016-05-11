app=angular.module('app', []);

app.controller('main', function($scope,$http) {
	$scope.list=[];
	$scope.book="";
	$scope.extension="";

	$scope.getList = function() {
		$http.get("/test/").then(
		function(data) {
			/*
			data.data=data.data.map(function(el) {
				if (el.STATUS!="DISCONNECTED")
					el.STATUS=el.STATUS+" "+el.ELAPSED;
				return el;
			});
			*/
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
	$scope.searchBook = function(book,extension){
		$http.post("/test/?ewqewqewq", {"type":"search","book":book,"extension":extension}).then(
		function(data) {
			console.log("success");
			$scope.getList();
		},
		function(data){
			console.log("err");
		});
	};
});
