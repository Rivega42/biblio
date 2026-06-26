# CENTRAL_SERVICE_API — приложение: точные тела запросов и все DTO центрального сервиса

> **Источник:** ПОЛНАЯ декомпиляция `LibraryAdminServer.WebService/WebService.cs` (1147 стр.) + 106 DataContract'ов. Сгенерировано автоматически из исходника.
> **Связанные:** [CENTRAL_SERVICE.md](CENTRAL_SERVICE.md) · [DEVICE_CONTROL_MAP.md](DEVICE_CONTROL_MAP.md) · [LAS_FUNCTION_MAP.md](LAS_FUNCTION_MAP.md)
> **Транспорт:** `POST {baseUrl}/{route}`, тело = `JsonConvert.SerializeObject(new {{ параметры }})`, `Content-Type: application/json`, `Authorization: Basic base64(login:password)`. Даты — Microsoft JSON (`/Date(ms+TZ)/`). Ответ — JSON `List<DTO>`/скаляр или поток (XLSX/ZIP). `byte[]`→`int[]`.
> **op/opID:** 0=удалить · 1=создать · 2=обновить · 3=смена пароля.

## 1. Каталог операций (route → тело запроса → ответ)

> ⚠️ Колонка «тело» = **сигнатура метода клиента**; обычно совпадает с фактически сериализуемым объектом, но есть исключения-баги исходника: `EntranceModify` НЕ шлёт `opID` (create/update различает по `entranceID==null`); `DesktopDeviceConfigGet` шлёт **пустое тело** (параметры теряются). В Biblio не воспроизводить.

| Операция | HTTP route | Тело запроса (параметры) | Ответ |
|---|---|---|---|
| `ACSGet` | `/las/ACSGet` | — | `<List<ACS_ACS>>` |
| `EntranceModify` | `/las/EntranceModify` | entranceID, entranceName, libraryID  _(opID в сигнатуре, но в тело НЕ идёт)_ | `<bool>` |
| `ACSEventsGet` | `/las/ACSEventsGet` | int? level, int? levelID, DateTime? startDate, DateTime? endDate, Guid? libraryID | `<List<ACS_Event>>` |
| `ACSAdvancedEventsGet` | `/las/ACSAdvancedEventsGet` | Guid? libraryID, DateTime? startDate, DateTime? endDate | `<List<ACS_AdvacedEvent>>` |
| `ACSReaderModify` | `/las/ACSReaderModify` | int? id, string name, string ipAddress, int? port, int? readerTypeID, int? entranceID | `<int>` |
| `ACSReaderAntennaAddModify` | `/las/ACSReaderAntennaAddModify` | int? id, string name, int? readerPortNumber, int? zoneID, int? readerID | `<bool>` |
| `ACSReaderAntennasGet` | `/las/ACSReaderAntennasGet` | Guid? libraryID | `<List<ACS_ReaderAntenna>>` |
| `ACSReaderTypesGet` | `/las/ACSReaderTypesGet` | — | `<List<ACS_ReaderType>>` |
| `ACSZoneModify` | `/las/ACSZoneModify` | int? id, string name, int? entranceID, int? directionTypeID | `<int>` |
| `LoginInfoGet` | `/las/LoginInfoGet` | string login, string password | `<AUTH_LoginInfo>` |
| `RoleTypesGet` | `/las/RoleTypesGet` | — | `<List<AUTH_RoleType>>` |
| `LoginModulesAccessGet` | `/las/LoginModulesAccessGet` | int? loginID | `<List<AUTH_LoginModulesAccess>>` |
| `UsersInfoGet` | `/las/UsersInfoGet` | — | `<List<AUTH_UserInfo>>` |
| `UserModify` | `/las/UserModify` | int? opID, string login, string oldPassword, string newPassword, string firstName, string secondName, string lastName | `<int>` |
| `UserModulesAccessAddModify` | `/las/UserModulesAccessAddModify` | LoginModulesAccess lma | `<int>` |
| `LoginInfoModify` | `/las/LoginInfoModify` | int? opID, string login, string password, string newPassword, int? roleTypeID, string firstName, string secondName, string lastName | `<int>` |
| `LASColorsGet` | `/web/ColorsGet` | — | `<List<DIR_Color>>` |
| `FaceDetectDevicesAndCamerasGet` | `/web/FaceDetectDevicesAndCamerasGet` | — | `<List<FD_DeviceAndCamera>>` |
| `FaceDetectStationsGet` | `/web/FaceDetectStationsGet` | Guid? libraryID | `<List<FD_Station>>` |
| `FaceDetectCameraModify` | `/web/FaceDetectCameraModify` | int? opID, int? deviceID, int? cameraID, string name, int? channelNo, string login, string password, bool? isActive, bool? isUSB, string ip, int? brightness, int? contrast, int? sharpness | `<bool>` |
| `FaceDetectCameraToStationAttach` | `/web/FaceDetectCameraToStationAttach` | Guid? stationID, int? cameraID | `<bool>` |
| `FaceDetectDeviceModify` | `/web/FaceDetectDeviceModify` | int? opID, int? deviceID, string hardwareID, string ip, int? port, string login, string password, Guid? libraryID | `<bool>` |
| `LibrariesGet` | `/las/LibrariesGet` | — | `<List<LIB_Library>>` |
| `BooksGet` | `/las/BooksGet` | Guid? libraryID | `<List<LIB_Book>>` |
| `LibraryModify` | `/web/LibraryModify` | Guid? libraryID, string name, string fullName, string manager, string phone, string address, string comment | `<List<LIB_Book>>` |
| `BookCoverGet` | `/las/BookCoverGet` | int? bookID | `<List<byte[]>>` |
| `TSLibraryUpdate` | `/las/TSLibraryUpdate` | int? ts, Guid? libraryID | `<bool>` |
| `BookModify` | `/web/BookModify` | int? bookID, string bookCode, string bookName, string authorsName, string description, bool? isSpecial, byte[] coverByte, Guid? libraryID | `<bool>` |
| `BookToLibBooksAdd` | `/las/BookToLibBooksAdd` | string bookCode, string bookName, Guid? libraryID | `<int>` |
| `BookFromLibBooksGet` | `/las/BookFromLibBooksGet` | int? bookID, string bookCode, Guid? libraryID | `<List<LIB_BookInfo>>` |
| `KeyUpdate` | `/las/KeyUpdate` | int tagserviceCount, string tagServiceCountHash, Guid? libraryID | `<bool>` |
| `DeviceDataGet` | `/las/DeviceDataGet` | Guid deviceID, DateTime selectedDate | `<List<MON_DeviceData>>` |
| `DevicesLastHistoryGet` | `/las/DevicesLastHistoryGet` | Guid? libraryID | `<List<MON_DeviceLastHistory>>` |
| `DevicesGet` | `/las/DevicesGet` | — | `<List<MON_Device>>` |
| `DeviceModify` | `/las/DeviceModify` | int? opID, Guid? deviceID, string name, int? typeID, string cfg, string cfg2, Guid? libraryID | `<Guid?>` |
| `DeviceTypesGet` | `/las/DeviceTypesGet` | — | `<List<MON_DeviceType>>` |
| `GateDataGet` | `/las/GateDataGet` | Guid gateID, DateTime selectedDate | `<List<MON_GateData>>` |
| `GateAlarmGet` | `/las/GateAlarmGet` | int? id | `<List<MON_GateAlarm>>` |
| `CurrentDeviceGet` | `/las/DesktopDeviceInfoGet` | Guid? deviceID | `<List<MON_CurrentDesktopDevice>>` |
| `GateAlarmsGet` | `/las/GateAlarmsGet` | Guid gateID, DateTime startDate, DateTime endDate | `<List<MON_GateAlarmsCount>>` |
| `GateCountersGet` | `/las/GateCountersGet` | Guid gateID, DateTime startDate, DateTime endDate | `<List<MON_GateCounter>>` |
| `GateEASEventsGet` | `/las/GateEASEventsGet` | Guid gateID, DateTime startDate, DateTime endDate | `<List<MON_GateEASEvent>>` |
| `GateModify` | `/las/GateModify` | Guid? gateID, string name, string ipAddress, int? port, int typeID, int? cfgTypeID, Guid? libraryID, string counterName, string counterIPAddress, int? counterPort | `<bool>` |
| `GatesGet` | `/las/GatesGet` | — | `<List<MON_Gate>>` |
| `GateTypesGet` | `/las/GateTypesGet` | — | `<List<MON_GateType>>` |
| `ServicesGet` | `/las/ServicesGet` | — | `<List<MON_Service>>` |
| `StationDataGet` | `/las/StationDataGet` | Guid stationid, DateTime selectedDate | `<List<MON_StationData>>` |
| `StationEventStatsGet` | `/las/StationEventStatsGet` | Guid stationid, DateTime startdate, DateTime endDate | `<List<MON_StationEventStat>>` |
| `StationsEventsHistoryGet` | `/las/StationEventsHistoryGet` | Guid? libraryID, DateTime? dateFrom, DateTime? dateTo | `<List<MON_StationEventsHistory>>` |
| `StationModify` | `/las/StationModify` | Guid stationID, string name, Guid? libraryID | `<bool>` |
| `StationsGet` | `/las/StationsGet` | — | `<List<MON_Station>>` |
| `StationAliveMonitoringGet` | `/web/StationAliveMonitoringGet` | Guid? stationID, DateTime? date | `<List<MON_StationAliveMonitoring>>` |
| `ReaderInfoGet` | `/las/ReaderInfoGet` | int? id, string rfidCode | `<List<RDR_ReaderInfo>>` |
| `ReaderModify` | `/las/ReaderModify` | int? opID, int? readerID, string name, string abisCode, string rfidCode, string serialNumber, string email | `<int>` |
| `ReaderPhotoAdd` | `/las/ReaderPhotoAdd` | int? id, byte[] bytearray | `<bool>` |
| `ReaderPhotoDelete` | `/las/ReaderPhotoDelete` | int id | `<bool>` |
| `ReadersGet` | `/las/ReadersGet` | — | `<List<RDR_ReaderInfo>>` |
| `SafeKeeperInfoGet` | `/las/SafeKeeperInfoGet2` | Guid? safeKeeperID | `<List<SK_SafeKeeperInfo>>` |
| `HistoryGet` | `/las/SafeKeeperHistoryGet` | DateTime? dateFrom, DateTime? dateTo | `<List<SK_History>>` |
| `HistoryMasterGet` | `/las/SafeKeeperHistoryMasterGet` | DateTime? dateFrom, DateTime? dateTo | `<List<SK_HistoryMaster>>` |
| `MasterRFIDModify` | `/las/MasterRFIDModify` | int? opID, int? id, string rfidCode, string firstName, string secondName, string lastName | `<int>` |
| `OrdersGet` | `/las/OrdersGet` | — | `<List<SK_Order>>` |
| `OrderBookProcessedSet` | `/las/OrderBookProcessedSet` | string bookCode, int? orderID | `<bool>` |
| `OrderModify` | `/las/OrderModify` | int? opID, int? id, string number, int? cellNumber, string readerRFID, string readerFIO, int? stateID, Guid? safekeeperID, int loginID | `<int>` |
| `OrderBodyModify` | `/las/OrderBodyModify` | int? opID, int? id, int? orderID, string bookRFID, string bookInfo, bool? isVerified, bool isProcessed, int? modifierID | `<bool>` |
| `OrderBodyGet` | `/las/OrderBodyGet` | int? orderID | `<List<SK_OrderBody>>` |
| `MastersRFIDGet` | `/las/MastersRFIDGet` | — | `<List<SK_MasterRFID>>` |
| `SafeKeeperModify` | `/las/SafeKeeperModify` | int? opID, Guid? safeKeeperID, string name, Guid? libraryID | `<int>` |
| `SafeKeepersGet` | `/las/SafeKeepersGet` | — | `<List<SK_SafeKeeper>>` |
| `SafeKeepersForOrderGet` | `/las/SafeKeepersForOrderGet` | — | `<List<SK_SafeKeeper>>` |
| `SafeKeepersMasterRFIDGet` | `/las/SafeKeepersMasterRFIDGet` | int masterRFIDID | `<List<Guid?>>` |
| `SafeKeeperMasterRFIDModify` | `/las/SafeKeeperMasterRFIDModify` | int? opID, Guid? safekeeperID, int? masterRFIDID | `<bool>` |
| `BooksOnShelfGet` | `/las/BooksOnShelfGet` | Guid? stationID | `<List<SS_BookOnShelf>>` |
| `SmartShelfReturnsGet` | `/las/SmartShelfReturnsGet` | Guid? stationID, DateTime? startDate, DateTime? endDate | `<List<SS_Return>>` |
| `SmartShelfStatsGet` | `/las/SmartShelfStatGet` | Guid? stationID | `<List<SS_Stat>>` |
| `VendingsGet` | `/web/VendingsGet` | Guid? libraryID | `<List<MON_Station>>` |
| `BooksOnVendingStationGet` | `/web/BooksOnVendingStationGet` | Guid? stationID | `<List<VD_BookOnVending>>` |
| `VendingOrdersGet` | `/las/VendingOrdersGet` | DateTime? dateStart, DateTime? dateEnd | `<List<VD_VendingOrder>>` |
| `VendingsEventsHistoryGet` | `/las/VendingsEventsHistoryGet` | Guid? libraryID, DateTime? dateFrom, DateTime? dateTo | `<List<MON_StationEventsHistory>>` |
| `VendingsSafekeepersGet` | `/las/VendingsSafekeepersGet` | — | `<List<SK_SafeKeeper>>` |
| `BookCaseAddModify` | `/las/BookCaseAddModify` | int? opID, int? bookCaseID, string name, string coordinates, int? sectionID, Guid? libraryID | `<bool>` |
| `BookCasesAndShelvesGet` | `/las/BookCasesAndShelvesGet` | int? sectionID, Guid? libraryID | `<List<BK_BookCaseAndShelves>>` |
| `StationsWithCoordinatesGet` | `/las/StationsWithCoordinatesGet` | Guid? libraryID | `<List<BK_StationWithCoordinates>>` |
| `BookCaseSectionAddModify` | `/las/BookCaseSectionAddModify` | int? bookSectionID, string bookSectionName, Guid? libraryID, int? opID | `<bool>` |
| `BookCaseSectionsGet` | `/las/BookCaseSectionsGet` | Guid? libraryID | `<List<BK_BookCaseSection>>` |
| `BookCasesGet` | `/las/BookCasesGet` | Guid? libraryID | `<List<BK_Case>>` |
| `BookCellAddModify` | `/las/BookCellAddModify` | int? opID, int? bookShelfID, Guid? bookCellID | `<bool>` |
| `BookCellsOnShelfGet` | `/las/BookCellsOnShelfGet` | int? bookShelfID | `<List<BK_BookCell>>` |
| `BookKeepingBooksGet` | `/las/BookKeepingBooksGet` | Guid? libraryID | `<List<BK_Book>>` |
| `BookKeepingBookRemove` | `/las/BookKeepingBookRemove` | int? bookID | `<bool>` |
| `BookKeepingBookInfofGet` | `/las/BookKeepingBookInfoGet` | string bookCode, Guid? libraryID | `<List<BK_BookOnCell>>` |
| `BooksOnCellfGet` | `/las/BooksOnCellGet` | Guid? cellID, Guid? libraryID | `<List<BK_BookOnCell>>` |
| `BookShelfAddModify` | `/las/BookShelfAddModify` | int? opID, int? bookCaseID, int? bookShelfID, string name | `<bool>` |
| `BookKeepingBookToCellBind` | `/las/BookKeepingBookToCellBind` | int? bookID, Guid? bookCellID | `<bool>` |
| `BookKeepingHistoryAdd` | `/las/BookKeepingHistoryAdd` | int? bookID, Guid? bookCellID, int? invStateID, int? executorID | `<bool>` |
| `BookKeepingHistoryGet` | `/las/BookKeepingHistoryGet` | DateTime? dateFrom, DateTime? dateTo, Guid? libraryID | `<List<BK_History>>` |
| `BookKeepingSearch` | `/las/BookKeepingBookSearch` | string word, Guid? libraryID | `<List<BK_BookSearch>>` |
| `BookKeepingHistoryStatGet` | `/las/BookKeepingHistoryStatGet` | DateTime? dateFrom, DateTime? dateTo, Guid? libraryID | `<List<BK_HistoryStat>>` |
| `BookKeepingStationCoordinatesSet` | `/web/BookKeepingStationCoordinatesSet` | Guid stationID, string coordinates | `<bool>` |
| `BookKeepingBackgroundGet` | `/web/BookKeepingBackgroundGet` | Guid? libraryID | `<List<BK_Background>>` |
| `BookKeepingBackgroundModify` | `/web/BookKeepingBackgroundModify` | int? backgroundID, byte[] backgroundByte, Guid? libraryID | `<bool>` |
| `BookKeepingBackgroundOpacityModify` | `/web/BookKeepingBackgroundOpacityModify` | int? backgroundID, double? opacity, Guid? libraryID | `<bool>` |
| `BookKeepingEnvironmentGet` | `/web/BookKeepingEnvironmentGet` | Guid? libraryID | `<List<BK_Environment>>` |
| `BookKeepingEnvironmentModify` | `/web/BookKeepingEnvironmentModify` | int? opID, int? environmentID, int? colorID, string coordinates, Guid? libraryID | `<bool>` |
| `KPIVisitorsGet` | `/las/VisitorsGet` | int[] intCameraIDList, DateTime? dateStart, DateTime? dateEnd, int lastVisitorID | `<List<KPI_Visitor>>` |
| `KPIDailyEmployeeReportGet` | `/las/KPIEmployeeDailyReportGet` | string login | `<List<KPI_DailyReport>>` |
| `KPIServicesGet` | `/las/KPIServicesGet` | Guid? libraryID | `<List<KPI_Service>>` |
| `KPIServicesTypesGet` | `/las/KPIServicesTypesGet` | — | `<List<KPI_ServiceType>>` |
| `KPICamerasGet` | `/las/KPICamerasGet` | Guid? libraryID | `<List<KPI_Camera>>` |
| `KPIServiceModify` | `/las/KPIServiceModify` | int? id, string name, int? typeID, bool? isAuthRequired, bool? isDeleted, Guid? libraryID | `<bool>` |
| `KPIServiceApply` | `/las/KPIServiceApply` | string login, int? serviceID, int? readerID | `<bool>` |
| `KPIEmployeesGet` | `/web/KPI_EmployeesGet` | Guid? libraryID | `<List<KPI_Employee>>` |
| `KPIReportServicesGet` | `/web/KPI_ReportServicesGet` | Guid? libraryID, DateTime? dateStart, DateTime? dateEnd, string SearchString, int? sortID, int? sortDirection | `<List<KPI_Report>>` |
| `KPIServicesListGet` | `/web/KPI_ServicesGet` | Guid? libraryID | `<List<KPI_ReportService>>` |
| `InfoEquipmentGet` | `/las/info_EquipmentGet` | Guid? libraryID | `<List<INFO_Equipment>>` |
| `InfoEASGet` | `/las/info_EASGet` | DateTime? dateFrom, DateTime? dateTo, Guid? libraryID | `<List<INFO_EAS>>` |
| `InfoEASAdvancedGet` | `/las/info_EASAdvancedGet` | — | `<List<INFO_AdvancedEAS>>` |
| `InfoStationsGet` | `/las/info_StationsGet` | DateTime? dateFrom, DateTime? dateTo, Guid? libraryID | `<List<INFO_Station>>` |
| `InfoStationsAdvancedGet` | `/las/info_StationsAdvancedGet` | — | `<List<INFO_AdvancedStation>>` |
| `InfoDesktopDevicesGet` | `/las/info_DesktopDevicesGet` | DateTime? dateFrom, DateTime? dateTo, Guid? libraryID | `<List<INFO_DesktopDevice>>` |
| `InfoDesktopDevicesAdvancedGet` | `/las/info_DesktopDevicesAdvancedGet` | — | `<List<INFO_AdvancedDesktopDevice>>` |
| `InfoSafeKeepersGet` | `/las/info_SafeKeepersGet` | DateTime? dateFrom, DateTime? dateTo, Guid? libraryID | `<List<INFO_SafeKeeper>>` |
| `InfoSafeKeepersAdvancedGet` | `/las/info_SafeKeepersAdvancedGet` | — | `<List<INFO_AdvancedSafekeeper>>` |
| `InfoSmartShelvesGet` | `/las/info_SmartShelvesGet` | DateTime? dateFrom, DateTime? dateTo, Guid? libraryID | `<List<INFO_SmartShelf>>` |
| `InfoSmartshelvesAdvancedGet` | `/las/info_SmartshelvesAdvancedGet` | — | `<List<INFO_AdvancedSmartshelf>>` |
| `InfoACSGet` | `/las/info_ACSGet` | DateTime? dateFrom, DateTime? dateTo, Guid? libraryID | `<List<INFO_ACS>>` |
| `InfoACSAdvancedGet` | `/las/info_ACSAdvancedGet` | — | `<List<INFO_AdvancedACS>>` |
| `BannerAddModify` | `/las/BannerAddModify` | int? bannerID, string bannerName, DateTime? peridFrom, DateTime? periodTo, int? interval, int[] image, bool? isDeleted, bool? isEnabled, int? opID | `<int>` |
| `BannerTaskAddModify` | `/las/BannerTaskAddModify` | int? bannerID, Guid? stationID, bool? opID | `<bool>` |
| `BannersGet` | `/las/BannersGet` | — | `<List<MON_Banner>>` |
| `BannerStationsGet` | `/las/StationsByBannerIDGet` | int? bannerID | `<List<MON_BannerStation>>` |
| `GPT_GetAnalytics` | `/web/gpt/GetAnalytics` | Guid? libraryID, Guid? stationID, DateTime? startDate, DateTime? endDate, bool? requestType, string searchString | `<List<GPT_Analytics>>` |
| `GPT_GetDashboardMetrics` | `/web/gpt/GetDashboardMetrics` | Guid? libraryID, Guid? stationID, DateTime? startDate, DateTime? endDate | `<GPT_DashboardMetrics>` |
| `GPT_GetTopQueries` | `/web/gpt/GetTopQueries` | Guid? libraryID, Guid? stationID, DateTime? startDate, DateTime? endDate | `<List<GPT_TopQueriesReport>>` |
| `GPT_GetLanguages` | `/web/gpt/GetLanguages` | — | `<List<GPT_Language>>` |
| `GPT_GetVoiceAssistantSettings` | `/web/gpt/GetVoiceAssistantSettings` | Guid? libraryID | `<List<GPT_VoiceAssistantSettings>>` |
| `GPT_GetVoiceResponseTemplates` | `/web/gpt/GetVoiceResponseTemplates` | Guid? libraryID, bool? isActive | `<List<GPT_VoiceResponseTemplate>>` |
| `GPT_GetVoiceTypes` | `/web/gpt/GetVoiceTypes` | — | `<List<GPT_VoiceType>>` |
| `GPT_UpdateVoiceResponseTemplate` | `/web/gpt/UpdateVoiceResponseTemplate` | int? templateID, Guid? libraryID, string questionText, string answerText, bool? isActive, int? fontSize, string fontColor, string borderColor | `<bool>` |
| `GPT_UpdateVoiceAssistantSettings` | `/web/gpt/UpdateVoiceAssistantSettings` | Guid? stationID, bool? isEnabled, int? voiceTypeID, int? languageID, string prompt, string knowledgeBase, string stopWords, string aPI_KEY, string folderID | `<bool>` |
| `GPT_GetTemplateStations` | `/web/gpt/GetTemplateStations` | Guid? libraryID, int? templateID | `<List<GPT_TemplateStation>>` |
| `GPT_UpdateTemplateStations` | `/web/gpt/UpdateTemplateStations` | int? templateID, Guid? stationID, bool? isActive | `<bool>` |
| `SettingsGet` | `/web/SettingsGet` | int? loginID | `<PROP_Settings>` |
| `SettingsModify` | `/web/SettingsModify` | int? loginID, PROP_Settings settings | `<bool>` |
| `IsUpdateAvailable` | `/las/upd_IsUpdateAvailable` | List<string> versions | `<bool>` |
| `Update` | `/las/upd_Update` | List<string> versions | `<object>` |
| `UpdateInfoGet` | `/las/upd_UpdateInfoGet` | — | `<string[]>` |
| `ExternalLogAdd` | `/las/ExternalLogAdd` | int? logTypeID, string comment | `<bool>` |
| `ExternalLogGet` | `/las/ExternalLogGet` | — | `<List<LOG_ExternalLog>>` |
| `ManualGet` | `/web/ManualGet` | — | `<MemoryStream>` |
| `DesktopDeviceConfigGet` | `/web/DesktopDeviceConfigGet` | _(тело пустое — deviceID/connectionString в коде НЕ передаются, баг)_ | `<MemoryStream>` (ZIP) |

**Всего операций: 151.**

## 2. Полные схемы DataContract (DTO) — все 106

Формат: `поле : тип` (`?` = nullable) — точная форма JSON ответов и вложенных объектов.

### ACS_ACS
- `ID` : `int`
- `Name` : `string`
- `LibraryID` : `Guid`
- `ZoneID` : `int?`
- `ZoneName` : `string`
- `DirectionTypeID` : `int?`
- `DirectionTypeName` : `string`
- `ReaderID` : `int?`
- `ReaderTypeID` : `int`
- `ReaderTypeName` : `string`
- `IPAddress` : `string`
- `IsOnline` : `int`
- `Port` : `int?`
- `ReaderName` : `string`
- `AntennaID` : `int?`
- `AntennaName` : `string`
- `ReaderPortNumber` : `int?`

### ACS_AdvacedEvent
- `ID` : `int`
- `RFIDCode` : `string`
- `ClientName` : `string`
- `DateIn` : `DateTime`
- `DateOut` : `DateTime?`
- `MinutesBetween` : `int?`

### ACS_Event
- `ID` : `int`
- `EventDate` : `DateTime`
- `RFIDCode` : `string`
- `ClientName` : `string`
- `ReaderID` : `int`
- `DirectionTypeID` : `int`

### ACS_ReaderAntenna
- `ID` : `int`
- `ReaderPortNumber` : `int`
- `AntennaName` : `string`
- `ReaderID` : `int`
- `ZoneID` : `int`
- `ZoneName` : `string`

### ACS_ReaderType
- `ID` : `int`
- `Name` : `string`
- `PortsCount` : `int`

### AUTH_LoginInfo
- `ID` : `int`
- `DateCreated` : `DateTime`
- `Login` : `string`
- `FirstName` : `string`
- `SecondName` : `string`
- `LastName` : `string`
- `Expired` : `DateTime`
- `OwnerID` : `Guid`
- `OwnerName` : `string`
- `OwnerAddress` : `string`
- `Version` : `int`
- `TS1` : `string`
- `RoleId` : `int`
- `RoleName` : `string`
- `IsUseEKP` : `bool`
- `DateBP` : `DateTime?`
- `InternalDate` : `DateTime`
- `PaymentDate` : `DateTime?`

### AUTH_LoginModulesAccess
- `ID` : `int?`
- `ModuleName` : `string`
- `IsAllowed` : `bool?`
- `IsShowVisual` : `bool`

### AUTH_RoleType
- `ID` : `int`
- `Name` : `string`

### AUTH_UserInfo
- `ID` : `int?`
- `Login` : `string`
- `FirstName` : `string`
- `SecondName` : `string`
- `LastName` : `string`
- `Expired` : `DateTime`
- `DateCreated` : `DateTime`
- `IsDeleted` : `bool`
- `RoleTypeId` : `int`
- `RoleTypeName` : `string`
- `OldPassword` : `string`
- `NewPassword` : `string`

### BK_Background
- `ID` : `int`
- `Background` : `byte[]`
- `Opacity` : `double`
- `LibraryID` : `Guid`

### BK_Book
- `BookID` : `int`
- `BookName` : `string`
- `BookCode` : `string`
- `AuthorsName` : `string`
- `BookCaseSectionID` : `int`
- `BookCaseSectionName` : `string`
- `BookCaseID` : `int`
- `BookCaseName` : `string`
- `BookShelfID` : `int`
- `BookShelfName` : `string`
- `CellID` : `Guid`
- `CellNumber` : `int`
- `FullLocationName` : `string`
- `StateID` : `int`
- `StateName` : `string`

### BK_BookCaseAndShelves
- `BookCaseSectionID` : `int`
- `BookCaseSectionName` : `string`
- `BookCaseID` : `int`
- `BookCaseName` : `string`
- `BooksOnCaseCount` : `int?`
- `BooksOnCaseReturnedCount` : `int?`
- `BookShelvesCount` : `int?`
- `BookShelfID` : `int?`
- `BookShelfName` : `string`
- `BooksOnShelfReturnedCount` : `int?`
- `Coordinates` : `string`
- `LibraryID` : `Guid`
- `Childs` : `List<BK_BookCaseAndShelves>`

### BK_BookCaseSection
- `ID` : `int`
- `Name` : `string`
- `BookCasesCount` : `int?`
- `BooksInSectionCount` : `int?`
- `BooksReturnedCount` : `int?`

### BK_BookCell
- `ID` : `Guid`
- `Number` : `int`
- `BookShelfID` : `int`
- `BooksOnCellCount` : `int?`
- `BooksReturnedCount` : `int?`

### BK_BookOnCell
- `BookID` : `int`
- `BookName` : `string`
- `BookCode` : `string`
- `StateID` : `int`
- `StateName` : `string`
- `BookCellID` : `Guid`
- `BookCellNumber` : `int`
- `BookShelfID` : `int`
- `BookShelfName` : `string`
- `BookCaseID` : `int`
- `BookCaseName` : `string`
- `FullPlaceName` : `string`
- `BookState` : `BookInvStates`
- `IsSkip` : `bool`

### BK_BookSearch
- `BookID` : `int`
- `BookCode` : `string`
- `BookName` : `string`
- `BookCell_ID` : `Guid`
- `BookCellNumber` : `int`
- `BookShelfName` : `string`
- `BookCaseName` : `string`
- `PlaceFullName` : `string`
- `StateID` : `int`
- `StateName` : `string`

### BK_Case
- `BookCaseSectionID` : `int`
- `BookCaseSectionName` : `string`
- `BookCaseID` : `int`
- `BookCaseName` : `string`
- `BooksOnCaseCount` : `int?`
- `BookShelvesCount` : `int?`
- `LibraryID` : `Guid`
- `Coordinates` : `string`
- `BK_Canvas` : `Canvas`

### BK_Environment
- `ID` : `int`
- `ColorID` : `int`
- `Color_HTML` : `string`
- `Coordinates` : `string`
- `BK_Canvas` : `Canvas`

### BK_History
- `ID` : `int`
- `BookID` : `int`
- `BookCode` : `string`
- `BookName` : `string`
- `DateCreated` : `DateTime`
- `BookCell_ID` : `Guid`
- `BookCellNumber` : `int`
- `BookShelfName` : `string`
- `BookCaseName` : `string`
- `PlaceFullName` : `string`
- `StateID` : `int`
- `StateName` : `string`
- `InvStateID` : `int`
- `InvStateName` : `string`
- `ExecutorID` : `int?`
- `ExecutorName` : `string`

### BK_HistoryStat
- `BooksNewCount` : `int?`
- `BooksFoundCount` : `int?`
- `BooksNotFoundCount` : `int?`
- `BooksReplaceCount` : `int?`
- `BooksOverallCount` : `int?`
- `QRCodesCount` : `int?`
- `BooksSearchCount` : `int?`

### BK_StationWithCoordinates
- `StationID` : `Guid`
- `StationName` : `string`
- `StationTypeID` : `int`
- `SN` : `string`
- `Coordinates` : `string`
- `IP` : `string`
- `BK_Canvas` : `Canvas`

### BookToSearch
- `BookInvState` : `BookInvStates`

### CellState
- `BooksReaded` : `int`
- `BooksOnPlace` : `int`
- `BooksNotOnPlace` : `int`
- `BooksNew` : `int`
- `BooksOnBalance` : `int`
- `BooksOnShelf` : `List<BK_BookOnCell>`

### DIR_Color
- `ID` : `int`
- `Color_HTML` : `string`

### FD_DeviceAndCamera
- `CameraID` : `int?`
- `CameraName` : `string`
- `DeviceID` : `int`
- `CameraChannel` : `int?`
- `CameraLogin` : `string`
- `CameraPassword` : `string`
- `IsCameraActive` : `bool?`
- `CameraDateCreated` : `DateTime?`
- `IsUSB` : `bool?`
- `CameraIP` : `string`
- `Brightness` : `int?`
- `Contrast` : `int?`
- `Sharpness` : `int?`
- `HardwareID` : `string`
- `DeviceDateCreated` : `DateTime`
- `DeviceIP` : `string`
- `DevicePort` : `int`
- `DeviceLogin` : `string`
- `DevicePassword` : `string`
- `DeviceDateLastOnline` : `DateTime?`
- `LibraryID` : `Guid?`
- `IsAttached` : `int`
- `Childs` : `List<FD_DeviceAndCamera>`

### FD_DeviceCamera
- `ID` : `int`
- `Name` : `string`
- `DeviceID` : `int`
- `ChannelNo` : `int`
- `DateCreated` : `DateTime`
- `IsActive` : `bool`
- `DateLastOnline` : `DateTime?`
- `HardwareID` : `string`
- `IP` : `string`
- `Login` : `string`
- `Password` : `string`
- `Port` : `int`

### FD_Station
- `ID` : `Guid`
- `DateCreated` : `DateTime`
- `StationName` : `string`
- `StationTypeID` : `int`
- `StationTypeName` : `string`
- `LastUpdate` : `DateTime?`
- `SN` : `string`
- `DeviceCameraID` : `int?`
- `DeviceCameraName` : `string`
- `DeviceCameraFullName` : `string`
- `LibraryID` : `Guid`
- `LibraryName` : `string`
- `IsHaveCamera` : `int`

### GPT_Analytics
- `StationID` : `Guid`
- `StationName` : `string`
- `RequestType` : `string`
- `QuestionText` : `string`
- `AnswerText` : `string`
- `RequestCount` : `int?`
- `AvgSessionDuration` : `int?`
- `DateCreated` : `DateTime?`

### GPT_DashboardMetrics
- `ResultType` : `string`
- `TotalInteractions` : `int?`
- `AvgSessionDuration` : `int?`
- `TemplateUsagePercent` : `decimal?`
- `ActiveStationsCount` : `int?`
- `UniqueReadersCount` : `int?`

### GPT_Language
- `ID` : `int`
- `Name` : `string`
- `Code` : `string`

### GPT_TemplateStation
- `StationID` : `Guid`
- `StationName` : `string`
- `IsActive` : `bool`

### GPT_TopQueriesReport
- `QuestionText` : `string`
- `RequestCount` : `int?`

### GPT_VoiceAssistantSettings
- `StationID` : `Guid?`
- `StationName` : `string`
- `IsEnabled` : `bool?`
- `VoiceTypeID` : `int?`
- `VoiceTypeName` : `string`
- `LanguageID` : `int?`
- `LanguageName` : `string`
- `IsServiceAlive` : `bool?`
- `LastUpdated` : `DateTime?`
- `TypeID` : `int?`
- `TypeName` : `string`
- `SN` : `string`
- `Prompt` : `string`
- `KnowledgeBase` : `string`
- `StopWords` : `string`
- `API_KEY` : `string`
- `FolderID` : `string`

### GPT_VoiceResponseTemplate
- `ID` : `int`
- `LibraryID` : `Guid`
- `QuestionText` : `string`
- `AnswerText` : `string`
- `IsActive` : `bool`
- `FontSize` : `int`
- `FontColor` : `string`
- `BorderColor` : `string`
- `DateCreated` : `DateTime`
- `DateUpdated` : `DateTime?`

### GPT_VoiceType
- `ID` : `int`
- `Name` : `string`
- `Description` : `string`

### INFO_ACS
- `PassesPerDay` : `int`
- `PassesByPeriod` : `int`
- `MaxAVGPassesPerDay` : `int`
- `MinAVGPassesPerDay` : `int`
- `ReadersByPeriod` : `int`
- `MostActiveEntrance` : `string`
- `LeastActiveEntrance` : `string`
- `LastEntrance` : `string`
- `LastEntranceID` : `int?`
- `LastEntranceLibraryID` : `Guid?`
- `LastPassDate` : `DateTime?`

### INFO_AdvancedACS
- `ID` : `int`
- `Name` : `string`
- `PassesToday` : `int?`
- `UniquePassesToday` : `int?`
- `PassesByLastWeek` : `int?`
- `UniquePassesByLastWeek` : `int?`
- `PassesByCurrentMonth` : `int?`
- `UniquePassesByCurrentMonth` : `int?`
- `PassesByCurrentYear` : `int?`
- `UniquePassesByCurrentYear` : `int?`
- `PassesOverall` : `int?`
- `UniquePassesOverall` : `int?`
- `LastOperationDate` : `DateTime?`
- `LastOperationEventID` : `DateTime?`

### INFO_AdvancedDesktopDevice
- `ID` : `Guid`
- `Name` : `string`
- `OperationsToday` : `int`
- `OperationsByLastWeek` : `int`
- `OperationsByCurrentMonth` : `int`
- `OperationsByCurrentYear` : `int`
- `OperationsOverall` : `int`
- `LastOperation` : `DateTime`

### INFO_AdvancedEAS
- `ID` : `Guid`
- `Name` : `string`
- `AlarmsToday` : `int?`
- `AlarmsByLastWeek` : `int?`
- `AlarmsByCurrentMonth` : `int?`
- `AlarmsByCurrentYear` : `int?`
- `AlarmsOverall` : `int?`
- `LastAlarm` : `DateTime?`
- `LastBook` : `string`
- `IsAlive` : `int`

### INFO_AdvancedSafekeeper
- `ID` : `Guid`
- `Name` : `string`
- `KeepingsToday` : `int`
- `OrdersToday` : `int`
- `VendingsToday` : `int`
- `KeepingsByLastWeek` : `int`
- `OrdersByLastWeek` : `int`
- `VendingsByLastWeek` : `int`
- `KeepingsByCurrentMonth` : `int`
- `OrdersByCurrentMonth` : `int`
- `VendingsByCurrentMonth` : `int`
- `KeepingsByCurrentYear` : `int`
- `OrdersByCurrentYear` : `int`
- `VendingsByCurrentYear` : `int`
- `KeepingsOverall` : `int`
- `OrdersOverall` : `int`
- `VendingsOverall` : `int`
- `LastOperationDate` : `DateTime?`
- `LastOperationEventID` : `int`
- `IsAlive` : `int`

### INFO_AdvancedSmartshelf
- `ID` : `Guid`
- `Name` : `string`
- `BooktakesToday` : `int?`
- `CheckinsToday` : `int?`
- `BooktakesByLastWeek` : `int?`
- `CheckinsByLastWeek` : `int?`
- `BooktakesByCurrentMonth` : `int?`
- `CheckinsByCurrentMonth` : `int?`
- `BooktakesByCurrentYear` : `int?`
- `CheckinsByCurrentYear` : `int?`
- `BooktakesOverall` : `int?`
- `CheckinsOverall` : `int?`
- `LastOperationDate` : `DateTime?`
- `LastOperationEventID` : `int?`
- `LastBook` : `string`
- `IsAlive` : `int`

### INFO_AdvancedStation
- `ID` : `Guid`
- `Name` : `string`
- `CheckoutsToday` : `int?`
- `CheckinsToday` : `int?`
- `CheckoutsByLastWeek` : `int?`
- `CheckinsByLastWeek` : `int?`
- `CheckoutsByCurrentMonth` : `int?`
- `CheckinsByCurrentMonth` : `int?`
- `CheckoutsByCurrentYear` : `int?`
- `CheckinsByCurrentYear` : `int?`
- `CheckoutsOverall` : `int?`
- `CheckinsOverall` : `int?`
- `LastOperationDate` : `DateTime?`
- `LastOperationEventID` : `int?`
- `LastBook` : `string`
- `IsAlive` : `int`

### INFO_DesktopDevice
- `OperationsPerDay` : `int`
- `OperationsByPeriod` : `int`
- `MaxAVGOperationsPerDay` : `int`
- `MinAVGOperationsPerDay` : `int`
- `MostActiveDevice` : `string`
- `LeastActiveDevice` : `string`
- `LastDevice` : `string`
- `LastDeviceID` : `Guid?`
- `LastDeviceLibraryID` : `Guid?`
- `LastOperationDate` : `DateTime?`

### INFO_EAS
- `AlarmsPerDay` : `int`
- `AlarmsByPeriod` : `int`
- `MaxAVGAlarmsPerDay` : `int`
- `MinAVGAlarmsPerDay` : `int`
- `BooksByPeriod` : `int`
- `MostActiveSystem` : `string`
- `LeastActiveSystem` : `string`
- `LastSystem` : `string`
- `LastSystemID` : `Guid?`
- `LastSystemLibraryID` : `Guid?`
- `LastAlarmDate` : `DateTime?`

### INFO_Equipment
- `EASCount` : `int?`
- `StationsCount` : `int?`
- `DesktopDevicesCount` : `int?`
- `SafeKeepersCount` : `int?`
- `SmartShelvesCount` : `int?`
- `ACSCount` : `int?`
- `OverallCount` : `int?`

### INFO_SafeKeeper
- `PutThingsPerDay` : `int`
- `PutThingsByPeriod` : `int`
- `MaxAVGPutThingsPerDay` : `int`
- `MinAVGPutThingsPerDay` : `int`
- `MostActiveStation` : `string`
- `LeastActiveStation` : `string`
- `LastStation` : `string`
- `LastStationID` : `Guid?`
- `LastStationLibraryID` : `Guid?`
- `LastPutThingsDate` : `DateTime?`

### INFO_SmartShelf
- `ReturnsPerDay` : `int`
- `ReturnsByPeriod` : `int`
- `MaxAVGReturnsPerDay` : `int`
- `MinAVGReturnsPerDay` : `int`
- `ReadersByPeriod` : `int`
- `MostActiveStation` : `string`
- `LeastActiveStation` : `string`
- `LastStation` : `string`
- `LastStationID` : `Guid?`
- `LastStationLibraryID` : `Guid?`
- `LastReturnDate` : `DateTime?`

### INFO_Station
- `CheckinsPerDay` : `int`
- `CheckoutsByPeriod` : `int`
- `CheckinsByPeriod` : `int`
- `MaxAVGCheckinsPerDay` : `int`
- `MinAVGCheckinsPerDay` : `int`
- `ReadersByPeriod` : `int`
- `MostActiveStation` : `string`
- `LeastActiveStation` : `string`
- `LastStation` : `string`
- `LastStationID` : `Guid?`
- `LastStationLibraryID` : `Guid?`
- `LastCheckinDate` : `DateTime?`

### KPI_Camera
- `CameraID` : `int`
- `CameraName` : `string`
- `ChannelNo` : `int`
- `RegistratorID` : `int`
- `RegistratorName` : `string`

### KPI_DailyReport
- `HourValue` : `int`
- `ReadersPerHourCount` : `int?`
- `ServicesPerHourCount` : `int?`

### KPI_Employee
- `LoginID` : `int?`
- `EployeeName` : `string`

### KPI_Report
- `ServiceID` : `int`
- `ServiceName` : `string`
- `LibraryID` : `Guid`
- `AppliedCount` : `int?`
- `ReadersCount` : `int?`

### KPI_ReportService
- `ServiceID` : `int?`
- `ServiceName` : `string`

### KPI_Service
- `ID` : `int`
- `Name` : `string`
- `TypeID` : `int?`
- `TypeName` : `string`
- `IsAuthRequired` : `bool`
- `LibraryID` : `Guid`

### KPI_ServiceType
- `ID` : `int`
- `Name` : `string`

### KPI_Visitor
- `ReaderID` : `int?`
- `ReaderName` : `string`
- `ID` : `int?`
- `DateCreated` : `DateTime?`
- `CameraID` : `int?`
- `AbisCode` : `string`
- `RFIDCode` : `string`
- `SerialNumber` : `string`
- `Email` : `string`
- `Comment` : `string`
- `Photo` : `byte[]`
- `Image` : `BitmapImage`
- `IsHavePhoto` : `int`

### LIB_Book
_(без публичных авто-свойств)_

### LIB_BookInfo
- `ID` : `int`
- `BookName` : `string`
- `BookCode` : `string`
- `LibraryID` : `Guid`

### LIB_Library
- `ID` : `Guid?`
- `Name` : `string`
- `Fullname` : `string`
- `Manager` : `string`
- `Phone` : `string`
- `Address` : `string`
- `TagServiceCount` : `int`
- `TagServiceCountHash` : `string`
- `TS` : `int`
- `DateCreated` : `DateTime`
- `Comment` : `string`

### LIC_Version
- `Guid` : `Guid`
- `TS` : `int`

### LOG_ExternalLog
- `ID` : `int`
- `DateCreated` : `DateTime`
- `LogTypeID` : `int`
- `LogTypeName` : `string`
- `LoginID` : `int`
- `Comment` : `string`
- `ModifierName` : `string`
- `ModuleID` : `int`
- `ModuleName` : `string`

### MAIN_Internal
- `Name` : `Guid`
- `PaymentDate` : `DateTime?`
- `PaymentDemoMode` : `int?`
- `LastDeviceDataID` : `long`
- `LastGateEventsID` : `long`
- `LastGateAlarmsID` : `long`
- `LastGateCountersID` : `long`
- `LastStationEventsID` : `long`
- `DateBP` : `DateTime?`
- `InternalDate` : `DateTime`

### MAIN_Owner
- `Id` : `Guid`
- `Name` : `string`
- `DateCreated` : `DateTime`
- `Version` : `int`
- `TS1` : `string`

### MON_Banner
- `ID` : `int`
- `Name` : `string`
- `DateCreated` : `DateTime`
- `PeriodFrom` : `DateTime?`
- `PeriodTo` : `DateTime?`
- `Interval` : `int`
- `Image` : `byte[]`
- `LoginID` : `int`
- `IsDeleted` : `bool`
- `LoginName` : `string`
- `IsEnabled` : `bool`
- `BitmapImage` : `BitmapImage`

### MON_BannerStation
- `ID` : `Guid`
- `StationName` : `string`

### MON_CurrentDesktopDevice
- `ID` : `Guid`
- `DeviceName` : `string`
- `TypeID` : `int`
- `DeviceTypeName` : `string`
- `LibraryID` : `Guid`
- `LibraryName` : `string`

### MON_Device
- `ID` : `Guid`
- `Name` : `string`
- `DateCreated` : `DateTime`
- `LastUpdate` : `DateTime?`
- `IsOnline` : `int`
- `TypeCFGID` : `int`
- `TypeCFGName` : `string`
- `TypeID` : `int`
- `TypeName` : `string`
- `CFG` : `string`
- `CFG2` : `string`
- `LibraryID` : `Guid?`

### MON_DeviceData
- `EventID` : `int`
- `DeviceID` : `Guid`
- `DateValue` : `DateTime`
- `HourValue` : `int`
- `SoftOnlineCount` : `int`
- `DeviceOKCount` : `int`
- `DeviceErrorCount` : `int`
- `DeviceOKCount_Percent` : `decimal?`
- `DeviceStateID` : `int`
- `DeviceName` : `string`
- `LibraryID` : `Guid?`
- `DeviceTypeID` : `int`
- `DeviceCFGTypeID` : `int`
- `DeviceState` : `string`

### MON_DeviceLastHistory
- `DeviceID` : `Guid`
- `DeviceName` : `string`
- `LastDeviceActivity` : `DateTime?`
- `LastSoftwareActivity` : `DateTime?`

### MON_DeviceLicense
- `IsActiveForLicense` : `int`
- `ActiveCount` : `int?`
- `OwnerTagServiceCount` : `int?`
- `CFG` : `string`
- `CFG2` : `string`
- `OwnerTagServiceCountHash` : `string`
- `OwnerID` : `int?`

### MON_DeviceType
- `ID` : `int`
- `Name` : `string`
- `TypeCFGID` : `int`
- `TypeName` : `string`
- `ConnectionString` : `string`

### MON_Gate
- `ID` : `Guid`
- `Name` : `string`
- `IP` : `string`
- `Port` : `int?`
- `TypeID` : `int`
- `CFGTypeID` : `int`
- `TypeName` : `string`
- `CFGTypeName` : `string`
- `LastUpdate` : `DateTime?`
- `IsOnline` : `int`
- `LibraryID` : `Guid?`
- `CounterName` : `string`
- `CounterIP` : `string`
- `CounterPort` : `int`
- `IsCounterOnline` : `int`

### MON_GateAlarm
- `ID` : `int`
- `GateID` : `Guid`
- `Name` : `string`
- `UID` : `string`
- `BookName` : `string`
- `DateValue` : `DateTime`

### MON_GateAlarmsCount
- `Date` : `DateTime?`
- `AlarmsCount` : `int?`

### MON_GateCounter
- `Date` : `DateTime?`
- `ValueIn` : `int?`
- `ValueOut` : `int?`

### MON_GateData
- `ID` : `int`
- `GateID` : `Guid`
- `DateValue` : `DateTime`
- `EventID` : `int`
- `EventName` : `string`
- `EventTypeID` : `int`
- `EventTypeName` : `string`
- `Count` : `int`

### MON_GateEASEvent
- `ID` : `int`
- `GateID` : `Guid`
- `DateValue` : `DateTime`
- `UID` : `string`
- `BookName` : `string`
- `BookCode` : `string`
- `IsBook` : `int`

### MON_GateType
- `TypeID` : `int`
- `TypeName` : `string`
- `CFGTypeID` : `int`
- `CFGTypeName` : `string`

### MON_MonogateCountDevice
- `ID` : `Guid`
- `Name` : `string`
- `IP` : `string`
- `Port` : `int`
- `DateLastOnline` : `DateTime?`
- `GateID` : `Guid`

### MON_Service
- `ID` : `int`
- `TypeID` : `int`
- `TypeName` : `string`
- `IsOnline` : `int`
- `Version` : `string`
- `LibraryID` : `Guid?`
- `LibraryName` : `string`

### MON_Station
- `ID` : `Guid`
- `Name` : `string`
- `DateCreated` : `DateTime`
- `LastUpdate` : `DateTime?`
- `IsOnline` : `int`
- `SN` : `string`
- `TypeID` : `int`
- `TypeName` : `string`
- `LibraryID` : `Guid?`
- `IsReaderOk` : `int`
- `IsCardReaderOk` : `int`
- `IsPrinterOk` : `int`
- `IsABISOk` : `int`
- `IsControllerOk` : `int`
- `IsConveyorOk` : `int`
- `StationAliveMonitoring` : `List<MON_StationAliveMonitoring>`

### MON_StationAliveMonitoring
- `HourValue` : `int?`
- `AlivePercents` : `int?`

### MON_StationData
- `ID` : `int`
- `StationID` : `Guid`
- `DateEvent` : `DateTime`
- `EventID` : `int`
- `EventName` : `string`
- `EventTypeID` : `int`
- `EventTypeName` : `string`
- `Message` : `string`
- `Count` : `int?`
- `UserCode` : `string`
- `PairID` : `int?`

### MON_StationEventStat
- `AvgSessionDurationSec` : `int`
- `SessionCount` : `int?`
- `ReadersCount` : `int?`
- `ReaderDeclineCount` : `int`
- `ReaderAccountCount` : `int`
- `BookBorrowCount` : `int`
- `BookReturnCount` : `int`
- `BookRenewCount` : `int`
- `PrintCount` : `int`
- `RateCount` : `int`
- `BooksPutCount` : `int`
- `AvgBookBorrowCountDay` : `int?`
- `AvgBookReturnCountDay` : `int?`
- `AvgReadersCountDay` : `int?`
- `AvgBooksPutDay` : `int?`
- `AvgRateCountDay` : `int`
- `RenewCountByAccountPercent` : `int?`
- `PrintCountBySessionPercent` : `int?`
- `LoginSuccessPercent` : `int?`

### MON_StationEventsHistory
- `ID` : `int`
- `DateEvent` : `DateTime?`
- `StationID` : `Guid`
- `StationName` : `string`
- `EventID` : `int`
- `EventName` : `string`
- `Message` : `string`
- `UserCode` : `string`
- `UserName` : `string`

### PROP_Settings
- `AIS` : `PROP_AIS`
- `Common` : `PROP_Common`
- `Email` : `PROP_Email`
- `FaceDetect` : `PROP_FaceDetect`
- `Proxy` : `PROP_Proxy`

### RDR_ReaderInfo
- `ID` : `int`
- `DateCreated` : `DateTime`
- `Name` : `string`
- `BirthDate` : `DateTime?`
- `AbisCode` : `string`
- `RFIDCode` : `string`
- `SerialNumber` : `string`
- `Email` : `string`
- `Photo` : `byte[]`
- `ImgPhoto` : `BitmapImage`
- `IsHavePhoto` : `int`

### RDR_ReaderIwthPhotoID
- `ID` : `int`
- `ReaderID` : `int`

### RDR_ReaderPhoto
- `ID` : `int`
- `ReaderID` : `int`
- `Name` : `string`
- `Photo` : `byte[]`
- `IsDeleted` : `int?`

### RDR_ReaderWithoutPhoto
- `ID` : `int`
- `DateCreated` : `DateTime`
- `Name` : `string`
- `BirthDate` : `DateTime?`
- `AbisCode` : `string`
- `RFIDCode` : `string`
- `SerialNumber` : `string`
- `IsHavePhoto` : `int`

### SK_Child
- `ID` : `Guid`
- `DateCreated` : `DateTime`
- `Name` : `string`
- `CellsCount` : `int`
- `SerialNumber` : `string`
- `CellsState` : `long?`
- `ControllerIP` : `string`
- `LastDateAlive` : `DateTime`
- `IsOnline` : `int`
- `SafeKeeperTypeID` : `int`
- `LibraryID` : `int`
- `LibraryName` : `string`
- `CellShift` : `int`

### SK_History
- `Id` : `int`
- `DateCreated` : `DateTime`
- `CellNumber` : `int?`
- `SafeKeeperId` : `Guid`
- `SafeKeeperName` : `string`
- `EventTypeId` : `int`
- `EventTypeName` : `string`
- `ReaderRFID` : `string`
- `ReaderFIO` : `string`
- `LibraryID` : `Guid?`

### SK_HistoryMaster
- `Id` : `int`
- `DateCreated` : `DateTime`
- `CellNumber` : `int?`
- `SafeKeeperId` : `Guid`
- `SafeKeeperName` : `string`
- `EventTypeId` : `int`
- `EventTypeName` : `string`
- `MasterRFIDId` : `int`
- `MasterRFIDFIO` : `string`
- `LibraryID` : `Guid?`

### SK_MasterRFID
- `Id` : `int`
- `DateCreated` : `DateTime`
- `RFID` : `string`
- `FirstName` : `string`
- `SecondName` : `string`
- `LastName` : `string`
- `IsDeleted` : `bool`

### SK_Order
- `Id` : `int`
- `DateCreated` : `DateTime`
- `Number` : `string`
- `CellNumber` : `int?`
- `ReaderRFID` : `string`
- `StateId` : `int`
- `ReaderFIO` : `string`
- `LoginId` : `int?`
- `LoginLastName` : `string`
- `LoginFirstName` : `string`
- `LoginSecondName` : `string`
- `StateName` : `string`
- `SafeKeeperName` : `string`
- `LibraryID` : `Guid`
- `LibraryName` : `string`
- `SafeKeeperId` : `Guid`
- `CellNumberShifted` : `int?`

### SK_OrderBody
- `Id` : `int`
- `DateCreated` : `DateTime`
- `BookRFID` : `string`
- `BookInfo` : `string`
- `IsVerified` : `bool`
- `IsProcessed` : `bool`
- `DateVerified` : `DateTime?`
- `OrderId` : `int`
- `OrderNumber` : `string`
- `ReaderFIO` : `string`
- `ReaderRFID` : `string`
- `Authors` : `string`

### SK_SafeKeeper
- `ID` : `Guid`
- `DateCreated` : `DateTime`
- `Name` : `string`
- `CellsCount` : `int`
- `SerialNumber` : `string`
- `CellsState` : `long?`
- `IPAddress` : `string`
- `LastDateAlive` : `DateTime`
- `IsOnline` : `int`
- `SafeKeeperTypeID` : `int`
- `LibraryID` : `Guid?`
- `LibraryName` : `string`
- `CellShift` : `int`
- `BusyCellsCount` : `int`
- `VacantCellsCount` : `int`
- `StationAliveMonitoring` : `List<MON_StationAliveMonitoring>`

### SK_SafeKeeperInfo
- `StationID` : `Guid?`
- `StationTypeID` : `int?`
- `CellNo` : `int?`
- `UserFIO` : `string`
- `UserCode` : `string`
- `CellContent` : `string`
- `DateBusy` : `DateTime?`
- `IsBusy` : `bool?`
- `CellShift` : `int?`
- `StorageTime` : `int?`
- `StorageTimeHint` : `string`
- `CellContentDescription` : `string`

### SK_StorageOccupiedCellsFullData
- `ID` : `int`
- `ReaderRFID` : `string`
- `ReaderFIO` : `string`
- `DateOpen` : `DateTime`
- `CellNo` : `int`

### SK_StorageOccupiedCellsWithType
- `ID` : `int`
- `ReaderRFID` : `string`
- `CellNo` : `int`
- `SafeKeeperId` : `Guid`
- `SafeKeeperName` : `string`
- `SafeKeeperTypeID` : `int`

### SS_BookOnShelf
- `ID` : `int`
- `BookID` : `int`
- `BookName` : `string`
- `BookCode` : `string`
- `CountTakes` : `int`
- `BookRate` : `int?`
- `BookRateCount` : `int?`

### SS_Return
- `DateEvent` : `DateTime`
- `UserCode` : `string`
- `BookName` : `string`
- `BookCode` : `string`
- `ReaderName` : `string`
- `BookRate` : `int?`
- `BookRateCount` : `int?`

### SS_Stat
- `TakesCountToday` : `int?`
- `TakesCountOverall` : `int?`
- `PutCountToday` : `int?`
- `PutCountOverall` : `int?`
- `ReturnsCountToday` : `int?`
- `ReturnsCountOverall` : `int?`

### VD_BookOnVending
- `ID` : `int`
- `VendingStationID` : `Guid`
- `CellNumber` : `int?`
- `BookName` : `string`
- `BookCode` : `string`
- `MasterID` : `int`
- `UserCode` : `string`
- `DateIn` : `DateTime`
- `BookRate` : `int?`
- `BookRateCount` : `int?`

### VD_VendingOrder
- `Id` : `int`
- `DateCreated` : `DateTime`
- `Number` : `string`
- `ReaderRFID` : `string`
- `StateId` : `int`
- `SafeKeeperId` : `Guid?`
- `ReaderFIO` : `string`
- `LoginId` : `int?`
- `LoginLastName` : `string`
- `LoginFirstName` : `string`
- `LoginSecondName` : `string`
- `StateName` : `string`
- `SafeKeeperName` : `string`
- `LibraryID` : `Guid`
- `LibraryName` : `string`

### VoiceType
- `ID` : `int`
- `Name` : `string`
- `Description` : `string`

