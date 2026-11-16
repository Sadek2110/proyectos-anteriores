package com.example.model

enum class Language(val code: String, val displayName: String) {
    ES("es", "Español"),
    EN("en", "English"),
    FR("fr", "Français"),
    AR("ar", "العربية");

    companion object {
        fun fromCode(code: String): Language =
            entries.find { it.code.equals(code, ignoreCase = true) } ?: ES
    }
}

enum class Interest(val id: String, val labelEs: String, val labelEn: String, val labelFr: String, val labelAr: String) {
    HISTORY("history", "Historia", "History", "Histoire", "التاريخ"),
    ARCHITECTURE("architecture", "Arquitectura", "Architecture", "Architecture", "العمارة"),
    FOOD("food", "Gastronomía", "Food", "Gastronomie", "الطعام");

    fun getLabel(lang: Language): String = when (lang) {
        Language.ES -> labelEs
        Language.EN -> labelEn
        Language.FR -> labelFr
        Language.AR -> labelAr
    }
}

data class LocalizedText(
    val es: String,
    val en: String,
    val fr: String,
    val ar: String
) {
    fun get(lang: Language): String = when (lang) {
        Language.ES -> es
        Language.EN -> en
        Language.FR -> fr
        Language.AR -> ar
    }
}

data class Poi(
    val id: String,
    val name: String,
    val latitude: Double,
    val longitude: Double,
    val interests: List<String>,
    val source: String,
    val narration: LocalizedText,
    val detail: LocalizedText,
    val drawableResName: String
)

data class Route(
    val id: String,
    val name: LocalizedText,
    val stops: List<String>,
    val estimatedMinutes: Int
)

enum class TourStatus {
    NOT_STARTED,
    ACTIVE,
    COMPLETED,
    ABANDONED
}

data class Tour(
    val id: String,
    val routeId: String,
    val status: TourStatus,
    val visited: List<String>,
    val createdAt: String
)

data class Service(
    val id: String,
    val name: String,
    val kind: String, // "restaurant" or "experience"
    val description: String,
    val isDemo: Boolean
)

data class Slot(
    val id: String,
    val serviceId: String,
    val startsAt: String,
    val capacity: Int,
    val bookedCount: Int = 0
) {
    val available: Int
        get() = (capacity - bookedCount).coerceAtLeast(0)
}

enum class BookingStatus(val code: String) {
    REQUESTED("requested"),
    CONFIRMED("confirmed"),
    CANCELLED("cancelled"),
    REJECTED("rejected")
}

data class Booking(
    val id: String,
    val sessionId: String,
    val slotId: String,
    val serviceName: String,
    val kind: String,
    val isDemo: Boolean,
    val startsAt: String,
    val partySize: Int,
    val name: String,
    val contact: String,
    val status: BookingStatus,
    val language: String,
    val idempotencyKey: String,
    val createdAt: String
)

data class ChatMessage(
    val id: Long = System.currentTimeMillis(),
    val role: String, // "user" or "assistant"
    val text: String,
    val mode: String? = null, // "local", "gemini", "emergency", "local_fallback"
    val sources: List<ChatSource> = emptyList(),
    val createdAt: String = java.text.SimpleDateFormat("HH:mm", java.util.Locale.getDefault()).format(java.util.Date())
)

data class ChatSource(
    val title: String,
    val url: String
)

data class EmergencyService(
    val id: String,
    val kind: String, // "hospital", "police", "consular"
    val name: String,
    val address: String,
    val source: String,
    val directionsUrl: String?
)

data class UserProfile(
    val language: Language = Language.ES,
    val interests: Set<String> = emptySet(),
    val locationConsent: Boolean = false,
    val aiConsent: Boolean = false
)
