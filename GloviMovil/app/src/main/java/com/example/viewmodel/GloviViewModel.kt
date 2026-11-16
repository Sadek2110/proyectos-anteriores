package com.example.viewmodel

import android.app.Application
import android.speech.tts.TextToSpeech
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.data.AssistantEngine
import com.example.data.CatalogRepository
import com.example.model.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

enum class AppSection(val id: String) {
    HOME("home"),
    ROUTES("routes"),
    ASSISTANT("assistant"),
    BOOKINGS("bookings"),
    EMERGENCY("emergency"),
    PRIVACY("privacy"),
    ADMIN("admin")
}

data class GloviUiState(
    val section: AppSection = AppSection.HOME,
    val profile: UserProfile = UserProfile(),
    val tour: Tour? = null,
    val isTrackingGps: Boolean = false,
    val gpsNote: String? = null,
    val isSpeaking: Boolean = false,
    val services: List<Service> = emptyList(),
    val slots: List<Slot> = emptyList(),
    val bookings: List<Booking> = emptyList(),
    val messages: List<ChatMessage> = emptyList(),
    val isChatBusy: Boolean = false,
    val noticeMessage: String? = null,
    val adminAuthenticated: Boolean = false
)

class GloviViewModel(application: Application) : AndroidViewModel(application), TextToSpeech.OnInitListener {

    private val _uiState = MutableStateFlow(GloviUiState())
    val uiState: StateFlow<GloviUiState> = _uiState.asStateFlow()

    private var tts: TextToSpeech? = null
    private var isTtsReady = false

    init {
        tts = TextToSpeech(application, this)
        seedInitialServicesAndSlots()
    }

    override fun onInit(status: Int) {
        if (status == TextToSpeech.SUCCESS) {
            isTtsReady = true
            updateTtsLanguage(_uiState.value.profile.language)
        }
    }

    private fun updateTtsLanguage(language: Language) {
        if (!isTtsReady || tts == null) return
        val locale = when (language) {
            Language.ES -> Locale("es", "ES")
            Language.EN -> Locale.ENGLISH
            Language.FR -> Locale.FRENCH
            Language.AR -> Locale("ar")
        }
        tts?.language = locale
    }

    private fun seedInitialServicesAndSlots() {
        val demoRestaurant = Service(
            id = "demo-restaurant",
            name = "Restaurante de demostración",
            kind = "restaurant",
            description = "Reserva de prueba: no corresponde a un establecimiento real.",
            isDemo = true
        )
        val demoTour = Service(
            id = "demo-tour",
            name = "Paseo cultural de demostración",
            kind = "experience",
            description = "Experiencia de prueba: sin operador turístico real.",
            isDemo = true
        )

        val slotsList = mutableListOf<Slot>()
        val cal = Calendar.getInstance()
        val isoFormat = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
        isoFormat.timeZone = TimeZone.getTimeZone("UTC")

        for (day in 1..7) {
            val d1 = Calendar.getInstance().apply {
                add(Calendar.DAY_OF_YEAR, day)
                set(Calendar.HOUR_OF_DAY, 18)
                set(Calendar.MINUTE, 0)
                set(Calendar.SECOND, 0)
            }
            slotsList.add(
                Slot(
                    id = "slot-rest-$day",
                    serviceId = demoRestaurant.id,
                    startsAt = isoFormat.format(d1.time),
                    capacity = 8,
                    bookedCount = 0
                )
            )

            val d2 = Calendar.getInstance().apply {
                add(Calendar.DAY_OF_YEAR, day)
                set(Calendar.HOUR_OF_DAY, 9)
                set(Calendar.MINUTE, 0)
                set(Calendar.SECOND, 0)
            }
            slotsList.add(
                Slot(
                    id = "slot-tour-$day",
                    serviceId = demoTour.id,
                    startsAt = isoFormat.format(d2.time),
                    capacity = 8,
                    bookedCount = 0
                )
            )
        }

        _uiState.update {
            it.copy(
                services = listOf(demoRestaurant, demoTour),
                slots = slotsList
            )
        }
    }

    fun selectSection(section: AppSection) {
        _uiState.update { it.copy(section = section, noticeMessage = null) }
    }

    fun updateLanguage(lang: Language) {
        _uiState.update { it.copy(profile = it.profile.copy(language = lang)) }
        updateTtsLanguage(lang)
    }

    fun toggleInterest(interestId: String) {
        _uiState.update {
            val current = it.profile.interests.toMutableSet()
            if (current.contains(interestId)) {
                current.remove(interestId)
            } else {
                current.add(interestId)
            }
            it.copy(profile = it.profile.copy(interests = current))
        }
    }

    fun setLocationConsent(consent: Boolean) {
        _uiState.update { it.copy(profile = it.profile.copy(locationConsent = consent)) }
        if (!consent) {
            stopGpsTracking()
        }
    }

    fun setAiConsent(consent: Boolean) {
        _uiState.update { it.copy(profile = it.profile.copy(aiConsent = consent)) }
    }

    // --- Tour and Route Handling ---

    fun startTour() {
        val nowIso = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).format(Date())
        val newTour = Tour(
            id = UUID.randomUUID().toString(),
            routeId = "ceuta-centro",
            status = TourStatus.ACTIVE,
            visited = emptyList(),
            createdAt = nowIso
        )
        _uiState.update { it.copy(tour = newTour, noticeMessage = "Ruta iniciada") }
    }

    fun abandonTour() {
        stopGpsTracking()
        stopSpeaking()
        _uiState.update {
            it.copy(
                tour = it.tour?.copy(status = TourStatus.ABANDONED),
                noticeMessage = "Ruta abandonada"
            )
        }
    }

    fun startGpsTracking() {
        if (!_uiState.value.profile.locationConsent) return
        _uiState.update { it.copy(isTrackingGps = true, gpsNote = null) }
    }

    fun stopGpsTracking() {
        _uiState.update { it.copy(isTrackingGps = false, gpsNote = null) }
    }

    fun simulateArrival(poiId: String) {
        val tour = _uiState.value.tour ?: return
        if (tour.status != TourStatus.ACTIVE) return

        val visited = tour.visited.toMutableList()
        if (!visited.contains(poiId)) {
            visited.add(poiId)
        }
        val isCompleted = CatalogRepository.pois.all { visited.contains(it.id) }
        val updatedTour = tour.copy(
            visited = visited,
            status = if (isCompleted) TourStatus.COMPLETED else TourStatus.ACTIVE
        )
        _uiState.update { it.copy(tour = updatedTour) }

        // Speak the narration automatically upon arrival
        val poi = CatalogRepository.pois.find { it.id == poiId }
        if (poi != null) {
            val text = CatalogRepository.getLocalizedNarration(
                poi,
                _uiState.value.profile.language,
                _uiState.value.profile.interests
            )
            speakNarration(text)
        }
    }

    fun onLocationUpdated(latitude: Double, longitude: Double, accuracyMeters: Float) {
        val state = _uiState.value
        val tour = state.tour ?: return
        if (tour.status != TourStatus.ACTIVE) return

        if (accuracyMeters > 100f) {
            _uiState.update { it.copy(gpsNote = "accuracy") }
            return
        }

        val visited = tour.visited.toMutableList()
        var newlyVisitedPoi: Poi? = null

        for (poi in CatalogRepository.pois) {
            if (!visited.contains(poi.id)) {
                val distance = CatalogRepository.distanceMeters(
                    latitude, longitude, poi.latitude, poi.longitude
                )
                if (distance <= 100.0) {
                    visited.add(poi.id)
                    newlyVisitedPoi = poi
                    break
                }
            }
        }

        if (newlyVisitedPoi != null) {
            val isCompleted = CatalogRepository.pois.all { visited.contains(it.id) }
            _uiState.update {
                it.copy(
                    tour = tour.copy(
                        visited = visited,
                        status = if (isCompleted) TourStatus.COMPLETED else TourStatus.ACTIVE
                    ),
                    gpsNote = null
                )
            }
            val text = CatalogRepository.getLocalizedNarration(
                newlyVisitedPoi,
                state.profile.language,
                state.profile.interests
            )
            speakNarration(text)
        }
    }

    fun speakNarration(text: String) {
        if (!isTtsReady || tts == null) return
        tts?.stop()
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "GLOVI_NARRATION")
        _uiState.update { it.copy(isSpeaking = true) }
    }

    fun stopSpeaking() {
        tts?.stop()
        _uiState.update { it.copy(isSpeaking = false) }
    }

    // --- Assistant / Chat ---

    fun sendChatMessage(userText: String) {
        val text = userText.trim()
        if (text.isEmpty() || _uiState.value.isChatBusy) return

        val state = _uiState.value
        val userMsg = ChatMessage(role = "user", text = text)

        val updatedMessages = (state.messages + userMsg).takeLast(40)
        _uiState.update { it.copy(messages = updatedMessages, isChatBusy = true) }

        viewModelScope.launch {
            try {
                val (reply, sources) = AssistantEngine.getLocalResponse(
                    text,
                    state.profile.language,
                    state.profile.interests
                )
                val intent = AssistantEngine.detectIntent(text)
                val mode = when {
                    intent == "emergency" -> "emergency"
                    state.profile.aiConsent && intent == "visit" -> "gemini"
                    else -> "local"
                }

                val assistantMsg = ChatMessage(
                    role = "assistant",
                    text = reply,
                    mode = mode,
                    sources = sources
                )

                _uiState.update {
                    it.copy(
                        messages = (it.messages + assistantMsg).takeLast(40),
                        isChatBusy = false
                    )
                }
            } catch (e: Exception) {
                _uiState.update { it.copy(isChatBusy = false) }
            }
        }
    }

    // --- Bookings ---

    fun createBooking(
        slotId: String,
        partySize: Int,
        name: String,
        contact: String
    ): Boolean {
        val state = _uiState.value
        val slot = state.slots.find { it.id == slotId } ?: return false
        val service = state.services.find { it.id == slot.serviceId } ?: return false

        if (slot.available < partySize) return false

        val idempotencyKey = UUID.randomUUID().toString()
        val booking = Booking(
            id = UUID.randomUUID().toString(),
            sessionId = "session-local",
            slotId = slot.id,
            serviceName = service.name,
            kind = service.kind,
            isDemo = service.isDemo,
            startsAt = slot.startsAt,
            partySize = partySize,
            name = name,
            contact = contact,
            status = BookingStatus.REQUESTED,
            language = state.profile.language.code,
            idempotencyKey = idempotencyKey,
            createdAt = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).format(Date())
        )

        val updatedSlots = state.slots.map {
            if (it.id == slotId) it.copy(bookedCount = it.bookedCount + partySize) else it
        }

        _uiState.update {
            it.copy(
                bookings = listOf(booking) + it.bookings,
                slots = updatedSlots,
                noticeMessage = "Reserva solicitada con éxito"
            )
        }
        return true
    }

    fun cancelBooking(bookingId: String) {
        val state = _uiState.value
        val booking = state.bookings.find { it.id == bookingId } ?: return

        val updatedSlots = state.slots.map {
            if (it.id == booking.slotId) {
                it.copy(bookedCount = (it.bookedCount - booking.partySize).coerceAtLeast(0))
            } else it
        }

        val updatedBookings = state.bookings.map {
            if (it.id == bookingId) it.copy(status = BookingStatus.CANCELLED) else it
        }

        _uiState.update {
            it.copy(bookings = updatedBookings, slots = updatedSlots, noticeMessage = "Reserva cancelada")
        }
    }

    // --- Admin Operations ---

    fun adminLogin(token: String): Boolean {
        if (token.trim().isNotEmpty()) {
            _uiState.update { it.copy(adminAuthenticated = true) }
            return true
        }
        return false
    }

    fun adminLogout() {
        _uiState.update { it.copy(adminAuthenticated = false) }
    }

    fun updateBookingStatus(bookingId: String, newStatus: BookingStatus) {
        val updatedBookings = _uiState.value.bookings.map {
            if (it.id == bookingId) it.copy(status = newStatus) else it
        }
        _uiState.update { it.copy(bookings = updatedBookings) }
    }

    fun addService(name: String, kind: String, description: String, isDemo: Boolean) {
        val newService = Service(
            id = "service-" + UUID.randomUUID().toString().take(6),
            name = name,
            kind = kind,
            description = description,
            isDemo = isDemo
        )
        _uiState.update { it.copy(services = it.services + newService) }
    }

    fun addSlot(serviceId: String, startsAt: String, capacity: Int) {
        val newSlot = Slot(
            id = "slot-" + UUID.randomUUID().toString().take(6),
            serviceId = serviceId,
            startsAt = startsAt,
            capacity = capacity,
            bookedCount = 0
        )
        _uiState.update { it.copy(slots = it.slots + newSlot) }
    }

    // --- Privacy & Reset ---

    fun exportDataJson(): String {
        val state = _uiState.value
        val sb = StringBuilder()
        sb.append("{\n")
        sb.append("  \"app\": \"GLOVI Ceuta\",\n")
        sb.append("  \"exportedAt\": \"${Date()}\",\n")
        sb.append("  \"profile\": {\n")
        sb.append("    \"language\": \"${state.profile.language.code}\",\n")
        sb.append("    \"interests\": [${state.profile.interests.joinToString { "\"$it\"" }}],\n")
        sb.append("    \"locationConsent\": ${state.profile.locationConsent},\n")
        sb.append("    \"aiConsent\": ${state.profile.aiConsent}\n")
        sb.append("  },\n")
        sb.append("  \"tour\": {\n")
        sb.append("    \"status\": \"${state.tour?.status ?: "NONE"}\",\n")
        sb.append("    \"visited\": [${state.tour?.visited?.joinToString { "\"$it\"" } ?: ""}]\n")
        sb.append("  },\n")
        sb.append("  \"bookingsCount\": ${state.bookings.size},\n")
        sb.append("  \"messagesCount\": ${state.messages.size}\n")
        sb.append("}")
        return sb.toString()
    }

    fun deleteAllData() {
        stopGpsTracking()
        stopSpeaking()
        _uiState.update {
            GloviUiState(
                profile = UserProfile(),
                noticeMessage = "Datos borrados. Se ha creado una sesión nueva."
            )
        }
        seedInitialServicesAndSlots()
    }

    override fun onCleared() {
        super.onCleared()
        tts?.stop()
        tts?.shutdown()
    }
}
