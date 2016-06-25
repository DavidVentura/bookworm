app=angular.module('app', []);

app.controller('main', function($scope,$http,$interval) {
	$scope.list=[];
	$scope.book="";
	$scope.extension="";

	$scope.activeTab = 'SEARCH';
	$scope.getList = function() {
		$http.get("http://192.168.1.7/test/").then(
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

		});
	}
	$scope.getList();

	$scope.download = function(book) {
		$http.post("http://192.168.1.7/test/?adasasd",{"type":"BOOK","book":book}).then(
		function(data) {
			$scope.getList();
		},
		function(data){
			console.log("error");
			console.log(data);
		});
	};
	$scope.searchBook = function(book,extension){
		$http.post("http://192.168.1.7/test/?ewqewqewq", {"type":"search","book":book,"extension":extension}).then(
		function(data) {
			console.log("success");
			$scope.getList();
		},
		function(data){
			console.log("err");
		});
	};

	$scope.isActiveTab = function(tab){
		return $scope.activeTab === tab;
	}

	$scope.changeTab = function(tab){
		$scope.activeTab = tab;
	}

	$scope.limit = {};
	$scope.showMore = function(l){
		$scope.limit[l.ID] = $scope.limit[l.ID] ? undefined : l.OUT.length;
	}
	$interval($scope.getList, 1000);
});
